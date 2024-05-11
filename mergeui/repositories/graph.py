import typing as t
import gqlalchemy as gq
from gqlalchemy.connection import _convert_memgraph_value
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.query_builders.memgraph_query_builder import Order
import core.db
from core.base import BaseRepository
from core.schema import Model, Graph


def _get_where_clause(q, where_initiated: bool):
    return getattr(q, "where" if not where_initiated else "and_where")


def _results_as_graph(results) -> Graph:
    if not results:
        return Graph()
    assert len(results) == 1, "Multiple results returned from query but only one expected."
    nodes = list(map(_convert_memgraph_value, results[0]["nodes"]))
    relationships = list(map(_convert_memgraph_value, results[0]["relationships"]))
    return Graph(nodes=nodes, relationships=relationships)


class GraphRepository(BaseRepository):
    def __init__(self, db_conn: 'core.db.DatabaseConnection'):
        self.db_conn = db_conn

    def list_property_values(self, *, key: str = "id", label: str = "") -> list[str]:
        """Get all possible values for a property including None"""
        q = (gq.match(connection=self.db_conn.db)
             .node(labels=label, variable="n")
             .return_(f"DISTINCT n.{key} as v")
             .order_by(properties=[("v", Order.ASC)]))
        return list(map(lambda x: x.get("v"), q.execute()))

    def list_nodes(
            self,
            *,
            label: str = "",
            limit: t.Optional[int] = None,
            **kwargs,
    ) -> list[gq.Node]:
        """Get all nodes with a specific label"""
        q = (
            gq.match(connection=self.db_conn.db)
            .node(labels=label, variable="n", **(kwargs or {}))
            .return_("DISTINCT n")
        )
        if limit is not None:
            q = q.limit(limit)
        result = list(map(lambda x: x.get("n"), q.execute()))
        return t.cast(list[gq.Node], result)

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

    def get_sub_graph(
            self,
            *,
            id_: str,
            label: str = "",
            relationship_type: str = "",
            max_depth: t.Optional[int] = None,
    ) -> Graph:
        """Get a sub-graph from a starting node"""
        if not id_:
            return Graph()
        q = (gq.match(connection=self.db_conn.db)
             .node(label, variable="n", id=id_))
        if relationship_type:
            rel_var = f"r:{relationship_type}"
        else:
            rel_var = "r"
        if max_depth is not None:
            q = q.to(variable=f"{rel_var}*..{max_depth}", directed=False)
        else:
            q = q.to(variable=f"{rel_var}*", directed=False)
        q = (
            q.node(label, variable="m")
            .with_("COLLECT(n)+COLLECT(m) AS all_nodes")
            .unwind("all_nodes", variable="node")
            .with_("COLLECT(DISTINCT node) AS distinct_nodes")
            .match()
            .node(label, variable="a")
            .to(variable="rel")
            .node(label, variable="b")
            .add_custom_cypher("WHERE a IN distinct_nodes AND b IN distinct_nodes")
            .with_("COLLECT(DISTINCT rel) AS distinct_rels, distinct_nodes")
            .return_("distinct_nodes AS nodes, distinct_rels as relationships")
        )
        results = list(q.execute())
        gr = _results_as_graph(results)
        if not gr.nodes:  # handle isolated node case
            q = (
                gq.match(connection=self.db_conn.db)
                .node(label, variable="n", id=id_)
                .return_("COLLECT(DISTINCT n) AS nodes, [] AS relationships")
            )
            results = list(q.execute())
            gr = _results_as_graph(results)
        return gr
