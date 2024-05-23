import typing as t
import pydantic as pd
from mergeui.core.schema import Model, ExcludeOptionType, SortByOptionType, DisplayColumnType
from mergeui.core.dependencies import get_settings
from mergeui.utils.types import create_partial_type_from_class

settings = get_settings()

LabelFieldType = t.Literal[
    "", "id", "name", "author", "license", "merge_method", "architecture", "likes", "downloads", "average_score",
    "arc_score", "hella_swag_score", "mmlu_score", "truthfulqa_score", "winogrande_score", "gsm8k_score"]
ColorFieldType = t.Literal[
    "author", "license", "merge_method", "architecture", "likes", "downloads", "average_score",
    "arc_score", "hella_swag_score", "mmlu_score", "truthfulqa_score", "winogrande_score", "gsm8k_score"]


class GetModelLineageInputDTO(pd.BaseModel):
    id: str = pd.Field(description="Model ID", min_length=1)
    directed: bool = pd.Field(True, description="Exclude children")
    max_hops: int = pd.Field(2, description="Max distance", ge=1, le=settings.max_hops)
    label_field: t.Optional[LabelFieldType] = pd.Field("name", description="Field to use as label")
    color_field: t.Optional[ColorFieldType] = pd.Field("average_score",
                                                       description="Field to use for generating colors")


class ListModelsInputDTO(pd.BaseModel):
    query: t.Optional[str] = pd.Field(None, description="Search query")
    sort_by: t.Optional[SortByOptionType] = pd.Field(None, description="Sort by")
    display_columns: t.Optional[t.List[DisplayColumnType]] = pd.Field(None, description="Columns to display")
    excludes: t.Optional[t.List[ExcludeOptionType]] = pd.Field(None, description="Exclude filters")
    author: t.Optional[str] = pd.Field(None, description="Author")
    license: t.Optional[str] = pd.Field(None, description="License")
    merge_method: t.Optional[str] = pd.Field(None, description="Merge strategy")
    architecture: t.Optional[str] = pd.Field(None, description="Model architecture")
    base_model: t.Optional[str] = pd.Field(None, description="Base model ID", min_length=1)
    limit: t.Optional[int] = pd.Field(settings.max_results, description="Max results")


DataT = t.TypeVar('DataT')


class GenericRO(pd.BaseModel, t.Generic[DataT]):
    model_config = pd.ConfigDict(arbitrary_types_allowed=True)
    success: bool = True
    message: t.Optional[str] = None
    data: t.Optional[DataT] = None


PartialModel = create_partial_type_from_class("PartialModel", Model, total=False)

DataFrameDataType = tuple[list[list], list[str], list[str]]


class DataGraph(pd.BaseModel):
    nodes: list[dict] = pd.Field(default_factory=list)
    relationships: list[dict] = pd.Field(default_factory=list)
