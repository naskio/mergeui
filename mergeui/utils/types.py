import typing as t
from typing_extensions import TypedDict


def create_partial_type_from_class(name: str, class_: t.Type) -> t.Type:
    """Create a TypedDict type from a class"""
    return TypedDict(name, class_.__annotations__.items(), total=False)


def create_fields_literal_type_from_class(class_: t.Type) -> t.Type:
    """Create a Literal type for field names from a class"""
    return t.Literal[tuple(class_.__annotations__.keys())]


def get_fields_from_class(class_: t.Type, type_: t.Optional[t.Type] = None, include_optionals: bool = False) \
        -> list[str]:
    """Get fields from a class that are of a specific type (not working well with list, dict)"""
    fields = []
    for field, field_type in class_.__annotations__.items():
        if (
                type_ is None
                or field_type == type_
                or (include_optionals and t.Optional[type_] == field_type)
        ):
            fields.append(field)
    return fields


def get_literal_type_options(type_: t.Type) -> list[str]:
    """Get options from a Literal type"""
    return list(t.get_args(type_))
