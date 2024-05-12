import typing as t
import pydantic as pd
from core.schema import Model, ExcludeOptionType, SortByOptionType, DisplayColumnType
from utils.types import create_partial_type_from_class

LabelFieldType = t.Literal[
    "id", "license", "merge_method", "architecture", "average_score", "arc_score", "hella_swag_score",
    "mmlu_score", "truthfulqa_score", "winogrande_score", "gsm8k_score"]
ColorFieldType = t.Literal[
    "license", "merge_method", "architecture", "average_score", "arc_score", "hella_swag_score",
    "mmlu_score", "truthfulqa_score", "winogrande_score", "gsm8k_score"]


class GetModelLineageInputDTO(pd.BaseModel):
    id: str = pd.Field(description="Model ID", min_length=1)
    label_field: t.Optional[LabelFieldType] = pd.Field("id", description="Field to use as label")
    color_field: t.Optional[ColorFieldType] = pd.Field("license", description="Field to use for generating colors")


class ListModelsInputDTO(pd.BaseModel):
    query: t.Optional[str] = pd.Field(None, description="Search query")
    sort_by: t.Optional[SortByOptionType] = pd.Field(None, description="Sort by")
    display_columns: t.Optional[t.List[DisplayColumnType]] = pd.Field(None, description="Columns to display")
    exclude: t.Optional[ExcludeOptionType] = pd.Field(None, description="Hide models")
    license: t.Optional[str] = pd.Field(None, description="License")
    merge_method: t.Optional[str] = pd.Field(None, description="Merge strategy")
    architecture: t.Optional[str] = pd.Field(None, description="Model architecture")
    base_model: t.Optional[str] = pd.Field(None, description="Base model ID", min_length=1)


DataT = t.TypeVar('DataT')


class GenericRO(pd.BaseModel, t.Generic[DataT]):
    success: bool = True
    message: t.Optional[str] = None
    data: t.Optional[DataT] = None

    class Config:
        arbitrary_types_allowed = True


PartialModel = create_partial_type_from_class("PartialModel", Model, total=False)

DataFrameDataType = tuple[list[list], list[str], list[str]]


class DataGraph(pd.BaseModel):
    nodes: list[dict] = pd.Field(default_factory=list)
    relationships: list[dict] = pd.Field(default_factory=list)
