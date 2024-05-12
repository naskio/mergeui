import typing as t
import gqlalchemy as gq
from gqlalchemy.connection import _convert_memgraph_value
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.query_builders.memgraph_query_builder import Order
import core.db
from core.base import BaseRepository
from core.schema import Model, Graph


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

    def list_property_values(self, *, key: str = "id", label: str = "", exclude_none: bool = False) -> list[str]:
        """Get all possible values for a property including None"""
        q = (
            gq.match(connection=self.db_conn.db)
            .node(labels=label, variable="n")
        )
        if exclude_none:
            q = q.add_custom_cypher(f"WHERE n.{key} IS NOT NULL")
        q = (
            q.return_(f"DISTINCT n.{key} as v")
            .order_by(properties=[("v", Order.ASC)])
        )
        return list(map(lambda x: x.get("v"), q.execute()))

    def list_nodes(
            self,
            *,
            label: str = "",
            limit: t.Optional[int] = None,
            filters: t.Optional[dict[str, t.Any]] = None,
    ) -> list[gq.Node]:
        """Get all nodes with a specific label"""
        q = (
            gq.match(connection=self.db_conn.db)
            .node(labels=label, variable="n", **(filters or {}))
            .return_("DISTINCT n")
        )
        if limit is not None:
            q = q.limit(limit)
        result = list(map(lambda x: x.get("n"), q.execute()))
        return t.cast(list[gq.Node], result)

    def get_sub_graph(
            self,
            *,
            start_id: str,
            label: str = "",
            relationship_type: str = "",
            max_depth: t.Optional[int] = None,
    ) -> Graph:
        """Get a sub-graph from a starting node"""
        if not start_id:
            return Graph()
        # get nodes
        q = (gq.match(connection=self.db_conn.db)
             .node(label, variable="n", id=start_id))
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
        )
        # get relationships
        q = (
            q.match()
            .node(label, variable="a")
            .to(relationship_type=relationship_type, variable="rel")
            .node(label, variable="b")
            .add_custom_cypher("WHERE a IN distinct_nodes AND b IN distinct_nodes")
            .with_("COLLECT(DISTINCT rel) AS distinct_rels, distinct_nodes")
            .return_("distinct_nodes AS nodes, distinct_rels as relationships")
        )
        results = list(q.execute())
        gr = _results_as_graph(results)
        if not gr.nodes:  # handle isolated node or empty graph
            q = (
                gq.match(connection=self.db_conn.db)
                .node(label, variable="n", id=start_id)
                .return_("COLLECT(DISTINCT n) AS nodes, [] AS relationships")
            )
            results = list(q.execute())
            gr = _results_as_graph(results)
        return gr
