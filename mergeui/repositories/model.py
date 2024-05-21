import typing as t
import shutil
import re
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
from utils import escaped, filter_none


def _get_where_clause(q, where_initiated: bool):
    return getattr(q, "where" if not where_initiated else "and_where")


class ModelRepository(BaseRepository):
    def __init__(self, db_conn: 'DatabaseConnection'):
        self.db_conn = db_conn
        self.settings = db_conn.settings
        self.index_dir = self.settings.project_dir / "media" / self.settings.text_index_name
        self.schema = self._get_schema()
        if self.settings.memgraph_text_search_disabled:
            self.query_parser = self._get_query_parser()
            self.index = None
            self.searcher = None
            if self.index_dir.exists() and self.index_dir.is_dir():
                self.index = whi.open_dir(self.index_dir)
                self.searcher = self.index.searcher()

    def __del__(self):
        if getattr(self, "searcher", None) is not None:
            self.searcher.close()

    def list_models(
            self,
            *,
            query: t.Optional[str] = None,
            label: str = "Model",
            not_label: t.Optional[str] = None,
            sort_key: t.Optional[str] = None,
            sort_order: t.Optional[Order] = None,
            sort_exclude_null_on_key: bool = False,
            base_model: t.Optional[str] = None,
            limit: t.Optional[int] = None,
            filters: t.Optional[dict[str, t.Any]] = None,
    ) -> list[Model]:
        """Get all models with optional filters"""
        base_model = escaped(base_model)
        where_initiated = False
        q = gq.match(connection=self.db_conn.db)
        # label and filters
        q = q.node(label, variable="n", **filter_none(escaped(filters) or {}))
        # base_model
        if base_model is not None:
            q = (q.to("DERIVED_FROM", variable="r")
                 .node("Model", variable="m", id=base_model))
        # not_label
        if not_label is not None:
            q = q.where_not("n", Operator.LABEL_FILTER, expression=not_label)
            where_initiated = True
        # exclude null on sort_key
        if sort_exclude_null_on_key and sort_key is not None:
            q = q.add_custom_cypher(f"{'AND' if where_initiated else 'WHERE'} n.{sort_key} IS NOT NULL")
            # noinspection PyUnusedLocal
            where_initiated = True
        # search query
        hits: t.Optional[set[str]] = None
        if query is not None and query.strip() != "":
            if not self.settings.memgraph_text_search_disabled:
                # https://quickwit.io/docs/reference/query-language#escaping-special-characters
                query = escaped(re.sub(r"[^-\w]+", "?", query))
                q = (
                    q.with_(
                        "n",
                    ).call("text_search.search_all", f"'{self.settings.text_index_name}', '{query}'")
                    .yield_("node")
                    .with_("n, node")
                    .where("n", Operator.EQUAL, expression="node")
                )
            else:
                hits = self._search_models(query, limit=limit)
        q = q.return_(f"DISTINCT n")
        # sort by
        if sort_key is not None:
            q = q.order_by(properties=[(f"n.{sort_key}", sort_order or Order.ASC)])
        # limit
        if limit is not None:
            q = q.limit(limit)
        result = map(lambda x: x.get("n"), execute_query(q) or [])
        # filter whoosh hits
        if hits is not None:
            result = filter(lambda m: m.id in hits, result)
        # return result
        result = list(result)
        return t.cast(list[Model], result)

    def create_text_search_index(self, reset_if_not_empty: bool = True) -> None:
        """Create text-search index for models in the file system"""
        logger.info(f"Creating text-search index '{self.settings.text_index_name}'...")
        if reset_if_not_empty:
            self.drop_text_search_index()
        if self._is_empty_text_search_index():
            self.index_dir.mkdir(parents=True, exist_ok=True)
            self.index = whi.create_in(self.index_dir, self.schema)
            writer = self.index.writer()
            models = self.list_models(limit=None)
            for model in models:
                writer.add_document(**self._get_document(model))
            writer.commit()
            self.searcher = self.index.searcher()
            logger.success(f"Text-search index '{self.settings.text_index_name}' created successfully")
        else:
            logger.info(f"Text-search index '{self.settings.text_index_name}' is not empty. Skipping creation.")

    def drop_text_search_index(self, force: bool = False) -> None:
        if force or not self._is_empty_text_search_index():
            logger.info(f"Resetting text-search index '{self.settings.text_index_name}'...")
            shutil.rmtree(self.index_dir)
            logger.success(f"Text-search index '{self.settings.text_index_name}' reset successfully")
        else:
            logger.info(f"Text-search index '{self.settings.text_index_name}' is already empty. Skipping reset.")

    def _is_empty_text_search_index(self) -> bool:
        return not self.index_dir.exists() or not (self.index_dir.is_dir() and list(self.index_dir.iterdir()))

    def _parse_query(self, q_str: str) -> whq.query.Query:
        parsed_q = q_str.lower() if not self.settings.whoosh_case_sensitive else q_str
        parsed_q = self.query_parser.parse(parsed_q)
        logger.trace(f"Parsed Query `{q_str}` => `{parsed_q}`")
        return parsed_q

    def _search_models(self, q_str: str, limit: t.Optional[int] = None) -> set[str]:
        """Search models using the text-search index"""
        if not self.settings.memgraph_text_search_disabled:
            raise NotImplementedError("You need to disable Memgraph text search to use Whoosh text-search.")
        parsed_q = self._parse_query(q_str)
        hits = self.searcher.search(parsed_q, limit=limit)
        return set(hit.get("original_id") for hit in hits)

    def _get_schema(self) -> whf.Schema:
        self.schema = whf.Schema(
            original_id=whf.STORED,
            id=whf.ID(field_boost=3.0, unique=True),
            name=whf.TEXT(field_boost=2.0),
            author=whf.TEXT(field_boost=2.0),
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
        if not self.settings.whoosh_case_sensitive:
            _doc = {k: str(v).lower() if v else v for k, v in _doc.items()}
        _doc["original_id"] = model.id
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
