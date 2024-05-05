from gqlalchemy.query_builders.memgraph_query_builder import Order

from core.base import BaseService
from core.schema import Model, Graph
from repositories.graph import GraphRepository
from utils import filter_none
from web.schema import GetModelLineageInputDTO, ListModelsInputDTO


class ModelService(BaseService):
    def __init__(self, repository: GraphRepository):
        self.repository = repository

    def get_model_lineage(
            self,
            inp: GetModelLineageInputDTO,
    ) -> Graph:
        return self.repository.get_sub_graph(
            id_=inp.id,
            label="Model",
            max_depth=self.repository.db_conn.settings.max_graph_depth,
        )

    def list_models(self, inp: ListModelsInputDTO) -> list[Model]:
        # exclude feature
        label, not_label = "Model", None
        if inp.exclude == "base models":
            label = "MergedModel"
        if inp.exclude == "merged models":
            not_label = "MergedModel"
        # sort feature
        sort_key, sort_order = None, None
        if inp.sort_by == "default":
            sort_key, sort_order = "created_at", Order.ASC
        elif inp.sort_by == "most likes":
            sort_key, sort_order = "likes", Order.DESC
        elif inp.sort_by == "most downloads":
            sort_key, sort_order = "downloads", Order.DESC
        elif inp.sort_by == "recently created":
            sort_key, sort_order = "created_at", Order.DESC
        elif inp.sort_by == "recently updated":
            sort_key, sort_order = "updated_at", Order.DESC
        return self.repository.list_models(
            query=None if not inp.query else inp.query,
            label=label,
            not_label=not_label,
            sort_key=sort_key,
            sort_order=sort_order,
            license_=inp.license,
            merge_method=inp.merge_method,
            architecture=inp.architecture,
            base_model=inp.base_model,
            limit=self.repository.db_conn.settings.results_limit,
        )

    def get_model_id_choices(self) -> list[str]:
        return filter_none(self.repository.list_property_values("id"))

    def get_license_choices(self) -> list[str]:
        return filter_none(self.repository.list_property_values("license"))

    def get_merge_method_choices(self) -> list[str]:
        return filter_none(self.repository.list_property_values("merge_method"))

    def get_architecture_choices(self) -> list[str]:
        return filter_none(self.repository.list_property_values("architecture"))
