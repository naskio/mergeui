import typing as t
import gqlalchemy as gq
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.query_builders.memgraph_query_builder import Order
import core.db
from core.base import BaseRepository
from core.schema import Model


def _get_where_clause(q, where_initiated: bool):
    return getattr(q, "where" if not where_initiated else "and_where")


class ModelRepository(BaseRepository):
    def __init__(self, db_conn: 'core.db.DatabaseConnection'):
        self.db_conn = db_conn

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
        if query is not None and query.strip() != "":
            q = (
                q.with_(
                    "n",
                ).call("text_search.search_all", f"'{self.db_conn.settings.text_index_name}', '{query}'")
                .yield_("node")
                .with_("n, node")
                .where("n", Operator.EQUAL, expression="node")
            )
        q = q.return_(f"DISTINCT n")
        if sort_key is not None:
            q = q.order_by(properties=[(f"n.{sort_key}", sort_order or Order.ASC)])
        if limit is not None:
            q = q.limit(limit)
        result = list(map(lambda x: x.get("n"), q.execute()))
        return t.cast(list[Model], result)
