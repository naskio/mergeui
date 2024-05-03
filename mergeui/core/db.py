from loguru import logger
import gqlalchemy as gq
import networkx as nx
from pathlib import Path
from core.settings import Settings
from core.base import BaseDatabaseConnection
from utils import parse_datetime
from utils.graph import load_json_nx_graph, import_from_nx_graph


class DatabaseConnection(BaseDatabaseConnection):
    settings: Settings
    db: gq.Memgraph

    def __init__(self, settings: Settings):
        logger.debug(f"Creating database connection for {settings.app_name}...")
        self.settings = settings
        self.db = gq.Memgraph()

    def reset(self):
        logger.info("Resetting database...")
        self.db.drop_database()
        logger.debug(f"Database dropped")
        for db_c in self.db.get_constraints():
            self.db.drop_constraint(db_c)
        logger.debug(f"Constraints dropped {self.db.get_constraints()}")
        for db_i in self.db.get_indexes():
            self.db.drop_index(db_i)
        self.db.execute(f"DROP TEXT INDEX {self.settings.text_index_name}")
        logger.debug(f"Indexes dropped {self.db.get_indexes()}")
        logger.success("Database reset completed.")

    def setup(self):
        logger.info("Setting up database...")
        self.db.create_index(gq.MemgraphIndex("Model"))
        self.db.create_index(gq.MemgraphIndex("Model", property="id"))
        logger.debug("Indexes created")
        self.db.create_constraint(gq.MemgraphConstraintExists("Model", property="id"))
        self.db.create_constraint(gq.MemgraphConstraintUnique("Model", property="id"))
        self.db.execute(f"CREATE TEXT INDEX {self.settings.text_index_name} ON :Model")
        logger.debug("Constraints created")
        logger.success("Database setup completed.")

    def populate_from_json(self, json_path: Path):
        graph = load_json_nx_graph(json_path)
        for node in graph.nodes:  # fix graph updated_at and created_at property types
            graph.nodes[node]["created_at"] = parse_datetime(graph.nodes[node]["created_at"])
            graph.nodes[node]["updated_at"] = parse_datetime(graph.nodes[node]["updated_at"])
        import_from_nx_graph(graph, self.db)

    def populate_from_nx_graph(self, graph: nx.Graph):
        import_from_nx_graph(graph, self.db)
