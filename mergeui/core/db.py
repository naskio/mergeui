import random
import typing as t
from loguru import logger
import datetime as dt
from pathlib import Path
import gqlalchemy as gq
import networkx as nx
import time
import core.settings
from core.schema import Model
from core.base import BaseDatabaseConnection
from utils import parse_iso_dt, aware_to_naive_dt
from utils.types import get_fields_from_class
from utils.nx import load_nx_graph_from_json_file, import_nx_graph_to_db


def create_db_connection(settings: 'core.settings.Settings') -> gq.Memgraph:
    logger.debug(f"Creating database connection for {settings.app_name}...")
    return gq.Memgraph(
        host=settings.mg_host,
        port=settings.mg_port,
        username=settings.mg_username,
        password=settings.mg_password,
        encrypted=settings.mg_encrypted,
        client_name=f"{settings.mg_client_name}_{random.randint(0, 500)}",
        lazy=settings.mg_lazy,
    )


def auto_retry_query(*, max_tries: t.Optional[int] = 10, delay: t.Optional[float] = None):
    """Decorator factory for auto-retrying query execution on DatabaseError."""

    def decorator(func):
        """Decorator for auto-retrying query execution on DatabaseError."""

        def wrapper(*args, **kwargs):
            _max_tries = max_tries
            _tries = 0
            _delay = delay
            while _tries < _max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    _e_str = e.__repr__()
                    logger.debug(f"Checking auto retry query for {_e_str}")
                    if any(sub_str in _e_str for sub_str in
                           ["Cannot resolve conflicting transactions", "failed to receive chunk size",
                            "GQLAlchemyWaitForConnectionError"]):
                        _tries += 1
                        if _max_tries is None or _tries < _max_tries:
                            logger.warning(f"Retrying query execution. Try {_tries} of {_max_tries}...")
                            if delay is None:
                                _delay = min(_tries / 10.0, 10.0)  # max 10s delay
                            time.sleep(_delay)
                    else:
                        raise  # Re-raise if it's a different DatabaseError

        return wrapper

    return decorator


@auto_retry_query()
def execute_query(q):
    result = q.execute()
    if isinstance(result, t.Iterator):
        result = list(result)
    return result


class DatabaseConnection(BaseDatabaseConnection):
    # for import_from_cypher_file, export_to_cypher_file: use Memgraph Lab UI
    settings: 'core.settings.Settings'
    db: gq.Memgraph

    def __init__(self, settings: 'core.settings.Settings'):
        self.settings = settings
        self.db = create_db_connection(self.settings)

    def setup(self, reset_if_not_empty: bool = True):
        logger.info("Setting up database...")
        if reset_if_not_empty and not self.is_empty():
            self.reset()
        # existing constraints
        self.db.create_constraint(gq.MemgraphConstraintExists("Model", property="id"))
        # unique constraints
        self.db.create_constraint(gq.MemgraphConstraintUnique("Model", property="id"))
        logger.debug("Constraints created")
        # label indexes
        self.db.create_index(gq.MemgraphIndex("Model"))
        self.db.create_index(gq.MemgraphIndex("MergedModel"))
        # property indexes
        self.db.create_index(gq.MemgraphIndex("Model", property="id"))
        # edge indexes
        self.db.execute(f"CREATE EDGE INDEX ON :DERIVED_FROM")
        # text index
        self.db.execute(f"CREATE TEXT INDEX {self.settings.text_index_name} ON :Model")
        logger.debug("Indexes created")
        logger.success("Database setup completed.")

    def reset(self):
        logger.info("Resetting database...")
        self.db.drop_database()
        logger.debug(f"Database dropped")
        for db_c in self.db.get_constraints():
            self.db.drop_constraint(db_c)
        logger.debug(f"Constraints dropped")
        for db_i in self.db.get_indexes():
            self.db.drop_index(db_i)
        self.db.execute(f"DROP EDGE INDEX ON :DERIVED_FROM")
        self.db.execute(f"DROP TEXT INDEX {self.settings.text_index_name}")
        logger.debug(f"Indexes dropped")
        assert self.is_empty(), "Database is not empty after reset."
        logger.success("Database reset completed.")

    def is_empty(self) -> bool:
        return not self.db.get_constraints() and not self.db.get_indexes()

    def populate_from_json_file(self, json_path: Path):
        graph: nx.Graph = load_nx_graph_from_json_file(json_path)
        for node in graph.nodes:  # handling dt.datetime fields
            for dt_field in get_fields_from_class(Model, dt.datetime, include_optionals=True):
                if dt_field in graph.nodes[node]:
                    value = graph.nodes[node][dt_field]
                    if value and isinstance(value, str):
                        graph.nodes[node][dt_field] = aware_to_naive_dt(parse_iso_dt(graph.nodes[node][dt_field]))
        import_nx_graph_to_db(graph, self.db)
