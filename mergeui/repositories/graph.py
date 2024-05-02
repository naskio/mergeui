from core.base import BaseRepository
import gqlalchemy as gq
import typing as t
import json
from core.schema import Model, MergedModel, DerivedFrom, Graph, SortByOptionType, ExcludeOptionType
from gqlalchemy.query_builders.memgraph_query_builder import Order
from gqlalchemy.query_builders.memgraph_query_builder import Operator
from gqlalchemy.vendors.database_client import DatabaseClient
from gqlalchemy.query_builders.memgraph_query_builder import Order


class GraphRepository(BaseRepository):
    def __init__(self, db: DatabaseClient):
        self.db = db

    def list_property_values(self, key: str = "id", label: str = "") -> list[str]:
        """Get all possible values for a property"""
        q = (gq.match()
             .node(labels=f"{label}", variable="n")
             .return_(f"DISTINCT n.{key} as v")
             .order_by(properties=[("v", Order.ASC)]))
        return list(map(lambda x: x.get("v"), q.execute()))

    def list_nodes(
            self,
            label: str = "",
    ) -> list[gq.Node]:
        """Get all nodes with a specific label"""
        q = (
            gq.match()
            .node(labels=label, variable="n")
            .return_("DISTINCT n")
        )
        result = list(map(lambda x: x.get("n"), q.execute()))
        return t.cast(list[gq.Node], result)

    def _get_where(self, q, first_where: bool):
        return getattr(q, "where" if first_where else "and_where")

    def list_models(
            self,
            query: t.Optional[str] = None,
            sort_by: t.Optional[SortByOptionType] = None,
            exclude: t.Optional[ExcludeOptionType] = None,
            license_: t.Optional[str] = None,
            merge_method: t.Optional[str] = None,
            architecture: t.Optional[str] = None,
            base_model: t.Optional[str] = None
    ) -> list[Model]:
        """Get all models with optional filters"""
        q = gq.match()
        f_where = True
        # exclude and base_model
        if exclude == "base":
            q = q.node("MergedModel", variable="n")
        else:
            q = q.node("Model", variable="n")
        if base_model is not None:
            q = (q.to("DERIVED_FROM", variable="r")
                 .node("Model", variable="m", id=base_model))
        if exclude == "merged":
            q = q.where_not("n", Operator.LABEL_FILTER, expression="MergedModel")
            f_where = False
        # license
        if license_ is not None:
            q = self._get_where(q, f_where)("n.license", Operator.EQUAL, literal=license_)
            f_where = False
        # merge_method
        if merge_method is not None:
            q = self._get_where(q, f_where)("n.merge_method", Operator.EQUAL, literal=merge_method)
            f_where = False
        # architecture
        if architecture is not None:
            q = self._get_where(q, f_where)("n.architecture", Operator.EQUAL, literal=architecture)
            f_where = False
        # search query
        if query is not None:
            q = (
                q.with_(
                    "n",
                ).call("text_search.search_all", f"'modelDocuments', '{query}'")
                .yield_("node")
                .with_("n, node")
                .where("n", Operator.EQUAL, expression="node")
            )
        q = q.return_(f"DISTINCT n")
        if sort_by is not None:
            if sort_by == "default":
                q = q.order_by(properties=[("n.created_at", Order.ASC)])
            elif sort_by == "most likes":
                q = q.order_by(properties=[("n.likes", Order.DESC)])
            elif sort_by == "most downloads":
                q = q.order_by(properties=[("n.downloads", Order.DESC)])
            elif sort_by == "recently created":
                q = q.order_by(properties=[("n.created_at", Order.DESC)])
            elif sort_by == "recently updated":
                q = q.order_by(properties=[("n.updated_at", Order.DESC)])
        result = list(map(lambda x: x.get("n"), q.execute()))
        return t.cast(list[Model], result)
