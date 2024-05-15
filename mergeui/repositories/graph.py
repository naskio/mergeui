import typing as t
import gqlalchemy as gq
from gqlalchemy.connection import _convert_memgraph_value
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.query_builders.memgraph_query_builder import Order
from core.db import DatabaseConnection, execute_query
from core.base import BaseRepository
from core.schema import Graph
from utils import filter_none, escaped


def _results_as_graph(results) -> Graph:
    if not results:
        return Graph()
    assert len(results) == 1, "Multiple results returned from query but only one expected."
    nodes = list(map(_convert_memgraph_value, results[0]["nodes"]))
    relationships = list(map(_convert_memgraph_value, results[0]["relationships"]))
    return Graph(nodes=nodes, relationships=relationships)


class GraphRepository(BaseRepository):
    def __init__(self, db_conn: 'DatabaseConnection'):
        self.db_conn = db_conn

    def list_property_values(
            self,
            *,
            key: str = "id",
            label: str = "",
            exclude_none: bool = False,
            filters: t.Optional[dict[str, t.Any]] = None,
            sort_by: t.Optional[t.Literal['count']] = None,
    ) -> list[str]:
        """Get all possible values for a property including None"""
        q = (
            gq.match(connection=self.db_conn.db)
            .node(labels=label, variable="n", **filter_none(escaped(filters) or {}))
        )
        if exclude_none:
            q = q.add_custom_cypher(f"WHERE n.{key} IS NOT NULL")
        q = (
            q.with_(
                f"n.{key} as v{', count(*) as count' if sort_by == 'count' else ''}"
            )
            .return_(f"DISTINCT v")
            .order_by(properties=([("count", Order.DESC)] if sort_by == 'count' else []) + [("v", Order.ASC)])
        )
        return list(map(lambda x: x.get("v"), execute_query(q) or []))

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
            .node(labels=label, variable="n", **filter_none(escaped(filters) or {}))
            .return_("DISTINCT n")
        )
        if limit is not None:
            q = q.limit(limit)
        result = list(map(lambda x: x.get("n"), execute_query(q) or []))
        return t.cast(list[gq.Node], result)

    def get_sub_graph(
            self,
            *,
            start_id: str,
            label: str = "",
            relationship_type: str = "",
            max_depth: t.Optional[int] = None,
    ) -> Graph:
        """Get a sub-graph from a starting node (use this if we want to include siblings)"""
        if not start_id:
            return Graph()
        start_id = escaped(start_id)
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
        results = execute_query(q)
        gr = _results_as_graph(results)
        if not gr.nodes:  # handle isolated node or empty graph
            q = (
                gq.match(connection=self.db_conn.db)
                .node(label, variable="n", id=start_id)
                .return_("COLLECT(DISTINCT n) AS nodes, [] AS relationships")
            )
            results = execute_query(q)
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
                **filter_none(escaped(filters) or {}),
            )
        )
        if new_values:
            q = q.set_(
                item="n",
                operator=Operator.INCREMENT,
                literal=filter_none(escaped(new_values)),
            )
        if new_labels:
            new_labels = [new_labels] if isinstance(new_labels, str) else new_labels
            q = q.add_custom_cypher(f"SET n:{':'.join(new_labels)}")
        if new_values or new_labels:
            execute_query(q)

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
                    **filter_none(escaped(filters) or {}),
                )
                .remove([f"n.{key}" for key in keys])
            )
            execute_query(q)

    def merge_nodes(
            self,
            *,
            label: str = "",
            src_id: str,
            dst_id: str,
            exclude_properties: t.Optional[t.List[str]] = None,
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
        src_id = escaped(src_id)
        dst_id = escaped(dst_id)
        # check if dst node exists
        q = (
            gq.match(connection=self.db_conn.db)
            .node(label, variable="n", id=dst_id)
            .return_("n")
        )
        results = execute_query(q)
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
        execute_query(q)
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
        execute_query(q)
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
        )
        if exclude_properties:
            q = q.remove([f"src.{key}" for key in exclude_properties])
        q = (
            q.set_("dst", Operator.ASSIGNMENT, expression="src")
            .delete(variable_expressions="src")
        )
        execute_query(q)

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
                **filter_none(escaped(filters) or {}),
            )
            .add_custom_cypher("ON CREATE")
            .set_(
                item="n",
                operator=Operator.INCREMENT,
                literal=filter_none(escaped(create_values)),
            )
            .add_custom_cypher("ON MATCH")
            .set_(
                item="n",
                operator=Operator.INCREMENT,
                literal=filter_none(escaped(update_values)),
            )
            .return_("n")
        )
        execute_query(q)

    def create_relationship(
            self,
            *,
            label: str = "",
            from_id: str,
            to_id: str,
            relationship_type: str = "",
            properties: t.Optional[dict[str, t.Any]] = None,
    ) -> None:
        from_id = escaped(from_id)
        to_id = escaped(to_id)
        q = (
            gq.match(connection=self.db_conn.db)
            .node(label, variable="src", id=from_id)
            .match()
            .node(label, variable="dst", id=to_id)
            .create()
            .node(variable="src")
            .to(relationship_type, True, variable="rel")
            .node(variable="dst")
            .set_("rel", Operator.INCREMENT, literal=filter_none(escaped(properties)))
            .return_("rel")
        )
        execute_query(q)

    def count_nodes(
            self,
            *,
            label: str = "",
            filters: t.Optional[dict[str, t.Any]] = None,
    ) -> int:
        q = (
            gq.match(connection=self.db_conn.db)
            .node(label, variable="n", **filter_none(escaped(filters) or {}))
            .return_("COUNT(DISTINCT n) as count")
        )
        results = execute_query(q)
        if results:
            return results[0].get("count", 0)
        return 0

    def get_sub_tree(
            self,
            *,
            start_id: str,
            label: str = "",
            relationship_type: str = "",
            directed: bool = False,
            max_depth: t.Optional[int] = None,
    ) -> Graph:
        """Get a Sub-Tree from a starting node (use this if we don't want to include siblings)"""
        if not start_id:
            return Graph()
        start_id = escaped(start_id)
        rel_var = ""
        if relationship_type:
            rel_var = f"{rel_var}:{relationship_type}"
        rel_var = f"{rel_var}*"
        if max_depth is not None:
            rel_var = f"{rel_var}..{max_depth}"
        q = (
            gq.match(connection=self.db_conn.db)
            .add_custom_cypher("path = ")
            .node(label, id=start_id)
            .to(variable=rel_var, directed=directed)
            .node(label)
            .with_("nodes(path) as all_nodes, relationships(path) as all_rels")
            .unwind("all_nodes", variable="node")
            .unwind("all_rels", variable="rel")
            .with_("COLLECT(DISTINCT node) as distinct_nodes, COLLECT(DISTINCT rel) as distinct_rels")
            .return_("distinct_nodes as nodes, distinct_rels as relationships")
        )
        results = execute_query(q)
        gr = _results_as_graph(results)
        if not gr.nodes:  # handle isolated node or empty graph
            q = (
                gq.match(connection=self.db_conn.db)
                .node(label, variable="n", id=start_id)
                .return_("COLLECT(DISTINCT n) AS nodes, [] AS relationships")
            )
            results = execute_query(q)
            gr = _results_as_graph(results)
        return gr
