import typing as t
import shutil
import gqlalchemy as gq
from loguru import logger
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.query_builders.memgraph_query_builder import Order
import whoosh.fields as whf
import whoosh.qparser as whq
import whoosh.index as whi
from core.db import DatabaseConnection, execute_query
from core.base import BaseRepository
from core.schema import Model
from utils import escaped


def _get_where_clause(q, where_initiated: bool):
    return getattr(q, "where" if not where_initiated else "and_where")


class ModelRepository(BaseRepository):
    def __init__(self, db_conn: 'DatabaseConnection'):
        self.db_conn = db_conn
        if self.db_conn.settings.memgraph_text_search_disabled:
            self.index_dir = db_conn.settings.project_dir / "media" / db_conn.settings.text_index_name
            self.schema = self._get_schema()
            self.query_parser = self._get_query_parser()
            self.index = None
            self.searcher = None
            if self.index_dir.exists() and self.index_dir.is_dir():
                self.index = whi.open_dir(self.index_dir)
                self.searcher = self.index.searcher()

    def __del__(self):
        if self.db_conn.settings.memgraph_text_search_disabled:
            if self.searcher is not None:
                self.searcher.close()

    def list_models(
            self,
            *,
            query: t.Optional[str] = None,
            label: str = "Model",
            not_label: t.Optional[str] = None,
            sort_key: t.Optional[str] = None,
            sort_order: t.Optional[Order] = None,
            exclude_null_on_sort_key: bool = False,
            license_: t.Optional[str] = None,
            merge_method: t.Optional[str] = None,
            architecture: t.Optional[str] = None,
            base_model: t.Optional[str] = None,
            limit: t.Optional[int] = None,
    ) -> list[Model]:
        """Get all models with optional filters"""
        query = escaped(query)
        base_model = escaped(base_model)
        q = gq.match(connection=self.db_conn.db)
        where_initiated = False
        # label
        q = q.node(label, variable="n")
        # base_model
        if base_model is not None:
            q = (q.to("DERIVED_FROM", variable="r")
                 .node("Model", variable="m", id=base_model))
        # not_label
        if not_label is not None:
            q = q.where_not("n", Operator.LABEL_FILTER, expression=not_label)
            where_initiated = True
        # license
        if license_ is not None:
            q = _get_where_clause(q, where_initiated)("n.license", Operator.EQUAL, literal=license_)
            where_initiated = True
        # merge_method
        if merge_method is not None:
            q = _get_where_clause(q, where_initiated)("n.merge_method", Operator.EQUAL, literal=merge_method)
            where_initiated = True
        # architecture
        if architecture is not None:
            q = _get_where_clause(q, where_initiated)("n.architecture", Operator.EQUAL, literal=architecture)
            where_initiated = True
        # exclude null on sort_key
        if exclude_null_on_sort_key and sort_key is not None:
            q = q.add_custom_cypher(f"{'AND' if where_initiated else 'WHERE'} n.{sort_key} IS NOT NULL")
            where_initiated = True
        # search query
        hits: t.Optional[set[str]] = None
        if query is not None and query.strip() != "":
            if not self.db_conn.settings.memgraph_text_search_disabled:
                q = (
                    q.with_(
                        "n",
                    ).call("text_search.search_all", f"'{self.db_conn.settings.text_index_name}', '{query}'")
                    .yield_("node")
                    .with_("n, node")
                    .where("n", Operator.EQUAL, expression="node")
                )
            else:
                hits = self._search_models(query, limit=limit)
        q = q.return_(f"DISTINCT n")
        if sort_key is not None:
            q = q.order_by(properties=[(f"n.{sort_key}", sort_order or Order.ASC)])
        if limit is not None:
            q = q.limit(limit)
        result = map(lambda x: x.get("n"), execute_query(q) or [])
        if hits is not None:
            if self.db_conn.settings.whoosh_case_sensitive:
                result = filter(lambda m: m.id in hits, result)
            else:
                result = filter(lambda m: str(m.id).lower() in hits, result)
        result = list(result)
        return t.cast(list[Model], result)

    def build_text_search_index(self, reset_if_not_empty: bool = True) -> None:
        """Create text-search index for models in the file system"""
        if not self.db_conn.settings.memgraph_text_search_disabled:
            raise NotImplementedError("You need to disable Memgraph text search to use Whoosh text-search.")
        logger.debug("Creating text-search index...")
        if reset_if_not_empty:
            self._reset_text_search_index()
        if self._is_empty_text_search_index():
            self.index_dir.mkdir(parents=True, exist_ok=True)
            self.index = whi.create_in(self.index_dir, self.schema)
            writer = self.index.writer()
            models = self.list_models(limit=None)
            for model in models:
                writer.add_document(**self._get_document(model))
            writer.commit()
            self.searcher = self.index.searcher()
            logger.success("Text-search index created successfully")
        else:
            logger.warning("Text-search index is not empty. Skipping creation.")

    def _reset_text_search_index(self, force: bool = False) -> None:
        if force or not self._is_empty_text_search_index():
            logger.info("Resetting text-search index...")
            shutil.rmtree(self.index_dir)
            logger.success("Text-search index reset successfully")
        else:
            logger.warning("Text-search index is already empty. Skipping reset.")

    def _is_empty_text_search_index(self) -> bool:
        return not self.index_dir.exists() or not (self.index_dir.is_dir() and list(self.index_dir.iterdir()))

    def _search_models(self, q_str: str, limit: t.Optional[int] = None) -> set[str]:
        """Search models using the text-search index"""
        if not self.db_conn.settings.memgraph_text_search_disabled:
            raise NotImplementedError("You need to disable Memgraph text search to use Whoosh text-search.")
        q_str = q_str.lower() if not self.db_conn.settings.whoosh_case_sensitive else q_str
        q = self.query_parser.parse(q_str)
        logger.trace(f"Parsed Query: {q}")
        results = set()
        hits = self.searcher.search(q, limit=limit)
        for hit in hits:
            results.add(hit.get("id"))
        return results

    def _get_schema(self) -> whf.Schema:
        self.schema = whf.Schema(
            id=whf.TEXT(stored=True, field_boost=3.0),  # , unique=True
            name=whf.ID(field_boost=2.0),
            author=whf.ID(field_boost=2.0),
            description=whf.TEXT(field_boost=1.0),
            license=whf.TEXT(field_boost=0.5),
            merge_method=whf.ID(field_boost=0.5),
            architecture=whf.KEYWORD(field_boost=0.5),
        )
        return self.schema

    def _get_document(self, model: Model) -> dict:
        _doc = dict(
            id=model.id,
            name=model.name,
            author=model.author,
            description=model.description,
            license=model.license,
            merge_method=model.merge_method,
            architecture=model.architecture,
        )
        if not self.db_conn.settings.whoosh_case_sensitive:
            _doc = {k: str(v).lower() if v else v for k, v in _doc.items()}
        return _doc

    def _get_query_parser(self) -> whq.QueryParser:
        # self.query_parser = whq.QueryParser("name", schema=self.schema, group=whq.OrGroup)
        self.query_parser = whq.MultifieldParser(
            ["id", "name", "author", "description", "license", "merge_method", "architecture"],
            schema=self.schema,
        )
        self.query_parser.remove_plugin_class(whq.FieldsPlugin)
        self.query_parser.remove_plugin_class(whq.WildcardPlugin)
        self.query_parser.remove_plugin_class(whq.PlusMinusPlugin)
        return self.query_parser
