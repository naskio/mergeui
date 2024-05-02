import pydantic as pd
import typing as t
import datetime as dt
import re
import stringcase

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
VarType = int


def var_factory(obj: pd.BaseModel) -> VarType:
    return id(obj)


class Node(pd.BaseModel):
    _var: VarType
    _labels: list[str]

    def __init__(self, **data):
        super().__init__(**data)
        self._var = var_factory(self)
        labels = []
        roots = self.__class__.__mro__
        for root in roots:
            if root in [Node, pd.BaseModel]:
                continue
            if not issubclass(root, pd.BaseModel):
                continue
            labels.append(stringcase.pascalcase(root.__name__))
        labels.reverse()
        self._labels = labels

    @property
    def var(self) -> VarType:
        return self._var

    @property
    def labels(self) -> list[str]:
        return self._labels


class Relationship(pd.BaseModel):
    _var: VarType
    _type: str
    _var_start: VarType
    _var_end: VarType

    def __init__(self, start: VarType, end: VarType, **data):
        super().__init__(**data)
        self._var = var_factory(self)
        self._type = stringcase.constcase(stringcase.sentencecase(self.__class__.__name__))
        self._var_start = start
        self._var_end = end

    @classmethod
    def from_nodes(cls, start: Node, end: Node, **data) -> "Relationship":
        return cls(start=start.var, end=end.var, **data)

    @property
    def var(self) -> VarType:
        return self._var

    @property
    def type(self) -> str:
        return self._type

    @property
    def var_start(self) -> VarType:
        return self._var_start

    @property
    def var_end(self) -> VarType:
        return self._var_end


class Graph(pd.BaseModel):
    nodes: t.List[Node] = pd.Field(default_factory=list)
    relationships: t.List[Relationship] = pd.Field(default_factory=list)


class Model(Node):
    id: str
    url: t.Optional[pd.AnyHttpUrl] = None
    name: t.Optional[str] = None
    description: t.Optional[str] = None
    license: t.Optional[str] = None
    author: t.Optional[str] = None
    merge_method: t.Optional[str] = pd.Field(None, description="Merge strategy")
    architecture: t.Optional[str] = None
    likes: t.Optional[int] = None
    downloads: t.Optional[int] = None
    created_at: t.Optional[dt.datetime] = None
    updated_at: t.Optional[dt.datetime] = None


class MergedModel(Model):
    pass


class DerivedFrom(Relationship):
    origin: str
    method: str


if __name__ == '__main__':
    g = Graph()
    n1 = Model(license="MIT", id="me/model1")
    g.nodes.append(n1)
    print(n1.dict(exclude_none=True), n1.labels, n1.var)
    n2 = MergedModel(id="me/model2")
    g.nodes.append(n2)
    print(n2.dict(exclude_none=True))
    r1 = DerivedFrom(var=1, start=n1.var, end=n2.var, origin="me", method="hi")
    r2 = DerivedFrom.from_nodes(start=n1, end=n2, origin="user", method="hola")
    g.relationships.append(r1)
    g.relationships.append(r2)
    print(r1.dict(exclude_none=True))
    print(r2.dict(exclude_none=True))
    print(g.nodes)
    print(g.relationships)
