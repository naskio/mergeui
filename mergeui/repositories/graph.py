import typing as t
import gqlalchemy as gq
from gqlalchemy.connection import _convert_memgraph_value
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.query_builders.memgraph_query_builder import Order
import core.db
from core.base import BaseRepository
from core.schema import Graph


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

    def set_properties(
            self,
            *,
            label: str = "",
            filters: t.Optional[dict[str, t.Any]] = None,
            create: bool = True,
            new_values: dict[str, t.Any],
            new_labels: t.Union[t.List[str], str] = "",
    ) -> None:
        """Set properties on matching nodes, create node it if it doesn't exist when create=True"""
        q = (
            getattr(gq, "merge" if create else "match")(connection=self.db_conn.db)
            .node(
                labels=label,
                variable="n",
                **(filters or {}),
            )
        )
        if new_values:
            q = q.set_(
                item="n",
                operator=Operator.INCREMENT,
                literal=new_values,
            )
        if new_labels:
            new_labels = [new_labels] if isinstance(new_labels, str) else new_labels
            q = q.add_custom_cypher(f"SET n:{':'.join(new_labels)}")
        if new_values or new_labels:
            q.execute()

    def remove_properties(
            self,
            *,
            label: str = "",
            filters: t.Optional[dict[str, t.Any]] = None,
            keys: t.Iterable[str],
    ) -> None:
        """Remove a list of properties from a node"""
        if keys:
            q = (
                gq.match(connection=self.db_conn.db)
                .node(
                    labels=label,
                    variable="n",
                    **(filters or {}),
                )
                .remove([f"n.{key}" for key in keys])
            )
            q.execute()

    def merge_nodes(
            self,
            *,
            label: str = "",
            src_id: str,
            dst_id: str,
    ) -> None:
        """
        Merge node src into node dst (properties and relationships are preserved)
        - if dst doesn't exist, just update src.id if it exists else do nothing
        - if dst exists and src doesn't exist, do nothing
        - if both exist:
        - move all incoming relationships of src to dst
        - move all outgoing relationships of src to dst
        - add src id and src.alt_ids to dst.alt_ids
        - then remove src
        """
        # check if dst node exists
        q = (
            gq.match(connection=self.db_conn.db)
            .node(label, variable="n", id=dst_id)
            .return_("n")
        )
        results = list(q.execute())
        if not results:  # dst node doesn't exist, just update src.id if it exists else do nothing
            return self.set_properties(
                label=label,
                filters=dict(id=src_id),
                new_values={"id": dst_id, "alt_ids": [src_id]},
                create=False,
            )
        # move all incoming relationships of src to dst
        q = (
            gq.match(connection=self.db_conn.db)
            .node(label)
            .to(variable="rel", directed=True)
            .node(label, id=src_id)
            .match()
            .node(label, variable="dst", id=dst_id)
            .call("refactor.to", "rel, dst")
            .yield_("relationship")
            .return_("relationship")
        )
        list(q.execute())
        # move all outgoing relationships of src to dst
        q = (
            gq.match(connection=self.db_conn.db)
            .node(label, id=src_id)
            .to(variable="rel", directed=True)
            .node(label)
            .match()
            .node(label, variable="dst", id=dst_id)
            .call("refactor.from", "rel, dst")
            .yield_("relationship")
            .return_("relationship")
        )
        list(q.execute())
        # copy src.alt_ids to dst.alt_ids and add src.id to dst.alt_ids
        # merge properties of src into dst if they don't exist in dst
        # then remove src node
        q = (
            gq.match(connection=self.db_conn.db)
            .node(labels=label, id=src_id, variable="src")
            .match()
            .node(labels=label, id=dst_id, variable="dst")
            .set_("dst.alt_ids", Operator.ASSIGNMENT,
                  expression=f"coalesce(dst.alt_ids, []) + coalesce(src.alt_ids, []) + '{src_id}'")
            .set_("src", Operator.INCREMENT, expression="dst")
            .set_("dst", Operator.ASSIGNMENT, expression="src")
            .delete(variable_expressions="src")
        )
        q.execute()

    def create_or_update(
            self,
            *,
            label: str = "",
            filters: t.Optional[dict[str, t.Any]] = None,
            create_values: dict[str, t.Any],
            update_values: dict[str, t.Any],
    ) -> None:
        """Create or update a node with a specific label and filters.
        - if exists, properties += {update_values}
        - else, create node with properties = {filters & create_values}
        """
        q = (
            gq.merge(connection=self.db_conn.db)
            .node(
                label,
                variable="n",
                **(filters or {}),
            )
            .add_custom_cypher("ON CREATE")
            .set_(
                item="n",
                operator=Operator.INCREMENT,
                literal=create_values,
            )
            .add_custom_cypher("ON MATCH")
            .set_(
                item="n",
                operator=Operator.INCREMENT,
                literal=update_values,
            )
            .return_("n")
        )
        list(q.execute())
