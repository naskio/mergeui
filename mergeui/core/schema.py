import typing as t
import dataclasses as dc
import datetime as dt
import gqlalchemy as gq
from core.settings import Settings
from utils.db import create_db_connection

db = create_db_connection(Settings())


@dc.dataclass
class Graph:
    nodes: t.List[gq.Node] = dc.field(default_factory=list)
    relationships: t.List[gq.Relationship] = dc.field(default_factory=list)


class Model(gq.Node):
    # Supported types: bool, int, float, str, list, dict, dt.datetime
    id: str = gq.Field(index=True, exists=True, unique=True, db=db)
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
