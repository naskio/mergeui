import pydantic as pd
import typing as t
import datetime as dt
import gqlalchemy as gq
from core.settings import Settings
from core.db_utils import create_db_connection
import re

DataT = t.TypeVar('DataT')


class GenericRO(pd.BaseModel, t.Generic[DataT]):
    success: bool = True
    message: t.Optional[str] = None
    data: t.Optional[DataT] = None

    class Config:
        arbitrary_types_allowed = True


MODEL_ID_REGEX = re.compile(r'^[-\w]+/[-\w]+$')

ColumnType = t.Literal[
    "id", "name", "description", "license", "author", "merge_method", "architecture",
    "likes", "downloads", "created_at", "updated_at"]
ExcludeOptionType = t.Literal["base", "merged"]
SortByOptionType = t.Literal["default", "most likes", "most downloads", "recently created", "recently updated"]
MergeMethodType = t.Literal[
    "linear", "slerp", "task_arithmetic", "ties", "dare_ties", "dare_linear", "passthrough",
    "breadcrumbs", "breadcrumbs_ties", "model_stock", "other"]


class Graph(pd.BaseModel):
    nodes: t.List[gq.Node] = pd.Field(default_factory=list)
    relationships: t.List[gq.Relationship] = pd.Field(default_factory=list)


class Model(gq.Node):
    # Supported types: bool, int, float, str, list, dict, dt.datetime
    id: str = gq.Field(index=True, exists=True, unique=True, db=create_db_connection(Settings()))
    url: t.Optional[str]  # pd.AnyHttpUrl can't be used
    name: t.Optional[str]
    description: t.Optional[str]
    license: t.Optional[str]
    author: t.Optional[str]
    merge_method: t.Optional[str] = gq.Field(description="Merge strategy")  # t.Optional[MergeMethodType] can't be used
    architecture: t.Optional[str]
    likes: t.Optional[int]
    downloads: t.Optional[int]
    created_at: t.Optional[dt.datetime]
    updated_at: t.Optional[dt.datetime]


class MergedModel(Model):
    pass


class DerivedFrom(gq.Relationship, type="DERIVED_FROM"):
    origin: str = gq.Field(description="Origin URL")
    method: str = gq.Field(description="Method used to extract data")
