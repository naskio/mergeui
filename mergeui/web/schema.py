import typing as t
import pydantic as pd
import datetime as dt
from core.schema import Model
from utils.types import get_fields_from_class, create_partial_type_from_class, create_literal_type

BaseValidationError = t.Union[pd.ValidationError, ValueError, AssertionError]

MODEL_FIELDS = get_fields_from_class(Model, include_optionals=True)
MODEL_DT_FIELDS = get_fields_from_class(Model, dt.datetime, include_optionals=True)
MODEL_INT_FIELDS = get_fields_from_class(Model, int, include_optionals=True)
MODEL_FLOAT_FIELDS = get_fields_from_class(Model, float, include_optionals=True)
DISPLAY_FIELDS = [field for field in MODEL_FIELDS if field not in Model.hidden_fields()]

PartialModel = create_partial_type_from_class("PartialModel", Model, total=False)

DisplayColumnType = create_literal_type(DISPLAY_FIELDS)

MergeMethodType = t.Literal["linear", "slerp", "task_arithmetic", "ties", "dare_ties", "dare_linear", "passthrough",
"breadcrumbs", "breadcrumbs_ties", "model_stock", "other"]
ExcludeOptionType = t.Literal["base models", "merged models"]
SortByOptionType = t.Literal["default", "most likes", "most downloads", "recently created", "recently updated",
"average score", "ARC", "HellaSwag", "MMLU", "TruthfulQA", "Winogrande", "GSM8k"]


class GetModelLineageInputDTO(pd.BaseModel):
    id: str = pd.Field(description="Model ID", min_length=1)


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


DataFrameDataType = tuple[list[list], list[str], list[str]]


class DataGraph(pd.BaseModel):
    nodes: list[dict] = pd.Field(default_factory=list)
    relationships: list[dict] = pd.Field(default_factory=list)
