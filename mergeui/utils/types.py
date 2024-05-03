import typing as t
from typing_extensions import TypedDict


def create_partial_type(name, base_type):
    return TypedDict(name, base_type.__annotations__.items(), total=False)


def create_literal_type(base_type):
    return t.Literal[tuple(base_type.__annotations__.keys())]
