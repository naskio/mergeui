import typing as t
from typing_extensions import TypedDict
import pydantic as pd
import re
import gqlalchemy as gq
from core.schema import Model
from utils.types import create_partial_type, create_literal_type

PartialModel = create_partial_type("PartialModel", Model)
PartialNode = create_partial_type("PartialNode", gq.Node)
PartialRelationship = create_partial_type("PartialRelationship", gq.Relationship)
ColumnType = create_literal_type(Model)


class Graph(TypedDict):
    nodes: list[PartialNode]
    relationships: list[PartialRelationship]


MODEL_ID_REGEX = re.compile(r'^[-.\w]+/[-.\w]+$')

MergeMethodType = t.Literal["linear", "slerp", "task_arithmetic", "ties", "dare_ties", "dare_linear", "passthrough",
"breadcrumbs", "breadcrumbs_ties", "model_stock", "other"]
ExcludeOptionType = t.Literal["base models", "merged models"]
SortByOptionType = t.Literal["default", "most likes", "most downloads", "recently created", "recently updated"]


class GetModelLineageInputDTO(pd.BaseModel):
    id: str = pd.Field(description="Model ID", pattern=MODEL_ID_REGEX, min_length=1)


class ListModelsInputDTO(pd.BaseModel):
    query: t.Optional[str] = pd.Field(None, description="Search query")
    sort_by: t.Optional[SortByOptionType] = pd.Field(None, description="Sort by")
    columns: t.Optional[t.List[ColumnType]] = pd.Field(None, description="Columns to show")
    exclude: t.Optional[ExcludeOptionType] = pd.Field(None, description="Hide models")
    license: t.Optional[str] = pd.Field(None, description="License")
    merge_method: t.Optional[str] = pd.Field(None, description="Merge strategy")
    architecture: t.Optional[str] = pd.Field(None, description="Model architecture")
    base_model: t.Optional[str] = pd.Field(None, description="Base model ID", pattern=MODEL_ID_REGEX)


DataT = t.TypeVar('DataT')


class GenericRO(pd.BaseModel, t.Generic[DataT]):
    success: bool = True
    message: t.Optional[str] = None
    data: t.Optional[DataT] = None

    class Config:
        arbitrary_types_allowed = True
