from typing import TypeGuard, TypeVar

from inspect_flow._types.flow_types import NotGiven

_T = TypeVar("_T")


def is_set(value: _T | NotGiven | None) -> TypeGuard[_T]:
    return not isinstance(value, NotGiven) and value is not None


def default(value: _T | NotGiven | None, default_value: _T) -> _T:
    return value if is_set(value) else default_value


def default_none(value: _T | NotGiven | None) -> _T | None:
    return default(value, None)
