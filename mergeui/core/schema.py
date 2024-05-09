import functools
import typing as t
import dataclasses as dc
import pydantic as pd
import datetime as dt
import gqlalchemy as gq
from utils import titlify
from utils.types import get_fields_from_class, create_literal_type


@dc.dataclass
class Graph:
    nodes: t.List[gq.Node] = dc.field(default_factory=list)
    relationships: t.List[gq.Relationship] = dc.field(default_factory=list)


class Model(gq.Node):
    # Supported types: bool, int, float, str, list, dict, dt.datetime
    id: str  # = gq.Field(index=True, exists=True, unique=True, db=get_db_connection().db)  # manage manually
    url: t.Optional[str]  # pd.AnyHttpUrl can't be used
    name: t.Optional[str]
    description: t.Optional[str]
    license: t.Optional[str]
    author: t.Optional[str]
    merge_method: t.Optional[str] = gq.Field(title="merge strategy")  # t.Optional[MergeMethodType] can't be used
    architecture: t.Optional[str]
    likes: t.Optional[int]
    downloads: t.Optional[int]
    created_at: t.Optional[dt.datetime]
    updated_at: t.Optional[dt.datetime]
    # evaluation
    arc_score: t.Optional[float] = gq.Field(title="ARC")
    hella_swag_score: t.Optional[float] = gq.Field(title="HellaSwag")
    mmlu_score: t.Optional[float] = gq.Field(title="MMLU")
    truthfulqa_score: t.Optional[float] = gq.Field(title="TruthfulQA")
    winogrande_score: t.Optional[float] = gq.Field(title="Winogrande")
    gsm8k_score: t.Optional[float] = gq.Field(title="GSM8K")
    average_score: t.Optional[float]
    evaluated_at: t.Optional[dt.datetime]
    # technical
    indexed: t.Optional[bool]
    indexed_at: t.Optional[dt.datetime]

    @classmethod
    @functools.cache
    def fields(cls) -> list[str]:
        return get_fields_from_class(cls, include_optionals=True)

    @classmethod
    @functools.cache
    def dt_fields(cls) -> list[str]:
        return get_fields_from_class(cls, dt.datetime, include_optionals=True)

    @classmethod
    @functools.cache
    def int_fields(cls) -> list[str]:
        return get_fields_from_class(cls, int, include_optionals=True)

    @classmethod
    @functools.cache
    def float_fields(cls) -> list[str]:
        return get_fields_from_class(cls, float, include_optionals=True)

    @classmethod
    def hidden_fields(cls) -> list[str]:
        return ["indexed", "indexed_at"]

    @classmethod
    @functools.cache
    def display_fields(cls) -> list[str]:
        return [field for field in cls.fields() if field not in cls.hidden_fields()]

    @classmethod
    def field_label(cls, key: str) -> str:
        return titlify(getattr(getattr(cls.__fields__.get(key, None), "field_info", None), "title", None) or key)


class MergedModel(Model):
    pass


class DerivedFrom(gq.Relationship, type="DERIVED_FROM"):
    origin: str = gq.Field(description="Origin URL")
    method: str = gq.Field(description="Method used to extract data")


BaseValidationError = t.Union[pd.ValidationError, ValueError, AssertionError]

SortByOptionType = t.Literal["default", "most likes", "most downloads", "recently created", "recently updated",
"average score", "ARC", "HellaSwag", "MMLU", "TruthfulQA", "Winogrande", "GSM8k"]
ExcludeOptionType = t.Literal["base models", "merged models"]
MergeMethodType = t.Literal["linear", "slerp", "task_arithmetic", "ties", "dare_ties", "dare_linear", "passthrough",
"breadcrumbs", "breadcrumbs_ties", "model_stock", "other"]

DisplayColumnType = create_literal_type(Model.display_fields())
