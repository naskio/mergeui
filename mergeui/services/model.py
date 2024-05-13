import typing as t
from gqlalchemy.query_builders.memgraph_query_builder import Order
from core.base import BaseService
import core.schema
from repositories import GraphRepository, ModelRepository


class ModelService(BaseService):
    def __init__(self, *, graph_repository: GraphRepository, model_repository: ModelRepository):
        self.gr = graph_repository
        self.mr = model_repository

    def get_model_lineage(
            self,
            *,
            model_id: str,
            max_depth: t.Optional[int] = None,
    ) -> 'core.schema.Graph':
        return self.gr.get_sub_graph(
            start_id=model_id,
            label="Model",
            max_depth=max_depth,
        )

    def list_models(
            self,
            *,
            query: t.Optional[str] = None,
            sort_by: t.Optional['core.schema.SortByOptionType'] = None,
            exclude: t.Optional['core.schema.ExcludeOptionType'] = None,
            license_: t.Optional[str] = None,
            merge_method: t.Optional[str] = None,
            architecture: t.Optional[str] = None,
            base_model: t.Optional[str] = None,
            limit: t.Optional[int] = None,
    ) -> list['core.schema.Model']:
        # exclude feature
        label, not_label = "Model", None
        if exclude == "base models":
            label = "MergedModel"
        if exclude == "merged models":
            not_label = "MergedModel"
        # sort feature
        sort_by_map = {
            "default": ("created_at", Order.ASC),
            "most likes": ("likes", Order.DESC),
            "most downloads": ("downloads", Order.DESC),
            "recently created": ("created_at", Order.DESC),
            "recently updated": ("updated_at", Order.DESC),
            "average score": ("average_score", Order.DESC),
            "ARC": ("arc_score", Order.DESC),
            "HellaSwag": ("hella_swag_score", Order.DESC),
            "MMLU": ("mmlu_score", Order.DESC),
            "TruthfulQA": ("truthfulqa_score", Order.DESC),
            "Winogrande": ("winogrande_score", Order.DESC),
            "GSM8k": ("gsm8k_score", Order.DESC),
        }
        if sort_by in sort_by_map:
            sort_key, sort_order = sort_by_map[sort_by]
        else:
            sort_key, sort_order = sort_by_map["default"]
        return self.mr.list_models(
            query=None if not query else query,
            label=label,
            not_label=not_label,
            sort_key=sort_key,
            sort_order=sort_order,
            exclude_null_on_sort_key=sort_order == Order.DESC,
            license_=license_,
            merge_method=merge_method,
            architecture=architecture,
            base_model=base_model,
            limit=limit,
        )

    def get_model_id_choices(self, private: t.Optional[bool] = None) -> list[str]:
        return self.gr.list_property_values(key="id", exclude_none=True, filters=dict(private=private))

    def get_license_choices(self) -> list[str]:
        return self.gr.list_property_values(key="license", exclude_none=True)

    def get_merge_method_choices(self) -> list[str]:
        return self.gr.list_property_values(key="merge_method", exclude_none=True)

    def get_architecture_choices(self) -> list[str]:
        return self.gr.list_property_values(key="architecture", exclude_none=True)

    def get_default_model_id(self) -> t.Optional[str]:
        top_models = self.mr.list_models(
            label="MergedModel",
            sort_key="average_score",
            sort_order=Order.DESC,
            exclude_null_on_sort_key=True,
            limit=1,
        )
        return top_models[0].id if top_models else None

    @property
    def db_conn(self):
        return self.mr.db_conn or self.gr.db_conn
