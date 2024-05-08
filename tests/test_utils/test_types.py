import typing as t
from utils.types import create_fields_literal_type_from_class, get_fields_from_class, \
    get_literal_type_options


class TestClass:
    a: str
    b: int
    c: t.List[str]


def test_create_fields_literal_type_from_class():
    assert create_fields_literal_type_from_class(TestClass) == t.Literal["a", "b", "c"]


def test_get_fields_from_class():
    assert get_fields_from_class(TestClass) == ["a", "b", "c"]
    assert get_fields_from_class(TestClass, type_=str) == ["a"]
    assert get_fields_from_class(TestClass, type_=int) == ["b"]
    assert get_fields_from_class(TestClass, type_=t.Optional[str]) == []
    assert get_fields_from_class(TestClass, type_=t.Optional[int]) == []
    assert get_fields_from_class(TestClass, type_=str, include_optionals=True) == ["a"]
    assert get_fields_from_class(TestClass, type_=int, include_optionals=True) == ["b"]
    assert get_fields_from_class(TestClass, type_=t.Optional[str], include_optionals=True) == []
    assert get_fields_from_class(TestClass, type_=t.Optional[int], include_optionals=True) == []
    assert get_fields_from_class(TestClass, type_=list) == []
    assert get_fields_from_class(TestClass, type_=list, include_optionals=True) == []


def test_get_literal_type_options():
    literal_type = t.Literal["a", "b", "c"]
    assert get_literal_type_options(literal_type) == ["a", "b", "c"]
