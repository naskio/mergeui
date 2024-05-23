import typing as t
from gqlalchemy.query_builders.memgraph_query_builder import Order
from mergeui.core.base import BaseService
from mergeui.core.schema import ExcludeOptionType, SortByOptionType, Graph, Model
from mergeui.repositories import GraphRepository, ModelRepository


class ModelService(BaseService):
    def __init__(self, *, graph_repository: GraphRepository, model_repository: ModelRepository):
        self.gr = graph_repository
        self.mr = model_repository

    def get_model_lineage(
            self,
            *,
            model_id: str,
            directed: bool = False,
            max_hops: t.Optional[int] = None,
    ) -> Graph:
        return self.gr.get_sub_tree(
            start_id=model_id,
            label="Model",
            relationship_type="DERIVED_FROM",
            directed=directed,
            max_hops=max_hops,
        )

    def list_models(
            self,
            *,
            query: t.Optional[str] = None,
            sort_by: t.Optional[SortByOptionType] = None,
            excludes: t.Optional[t.List[ExcludeOptionType]] = None,
            author: t.Optional[str] = None,
            license_: t.Optional[str] = None,
            merge_method: t.Optional[str] = None,
            architecture: t.Optional[str] = None,
            base_model: t.Optional[str] = None,
            limit: t.Optional[int] = None,
    ) -> list[Model]:
        # filters
        filters = {
            "author": author,
            "license": license_,
            "merge_method": merge_method,
            "architecture": architecture,
        }
        # excludes
        excludes = excludes or []
        label, not_label = "Model", None
        if "private" in excludes:
            filters["private"] = False
        if "gated" in excludes:
            filters["gated"] = False
        if "base models" in excludes:
            label = "MergedModel"
        if "merged models" in excludes:
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
        # get and return models
        return self.mr.list_models(
            query=None if not query else query,
            label=label,
            not_label=not_label,
            sort_key=sort_key,
            sort_order=sort_order,
            sort_exclude_null_on_key=sort_order == Order.DESC,
            base_model=base_model,
            limit=limit,
            filters=filters,
        )

    def get_model_id_choices(self, private: t.Optional[bool] = None, merged_only: bool = False) -> list[str]:
        label = "Model" if not merged_only else "MergedModel"
        return self.gr.list_property_values(key="id", label=label, exclude_none=True, filters=dict(private=private))

    def get_license_choices(self) -> list[str]:
        return self.gr.list_property_values(key="license", exclude_none=True, sort_by="count")

    def get_author_choices(self) -> list[str]:
        return self.gr.list_property_values(key="author", exclude_none=True, sort_by="count")

    def get_merge_method_choices(self) -> list[str]:
        return self.gr.list_property_values(key="merge_method", exclude_none=True, sort_by="count")

    def get_architecture_choices(self) -> list[str]:
        return self.gr.list_property_values(key="architecture", exclude_none=True, sort_by="count")

    def get_default_model_id(self) -> t.Optional[str]:
        top_models = self.mr.list_models(
            label="MergedModel",
            sort_key="average_score",
            sort_order=Order.DESC,
            sort_exclude_null_on_key=True,
            limit=1,
        )
        return top_models[0].id if top_models else None

    @property
    def db_conn(self):
        return self.mr.db_conn or self.gr.db_conn
