from itertools import chain
from typing import TypeVar

T = TypeVar("T")


def ensure_list(value: list[T] | None) -> list[T]:
    return value if isinstance(value, list) else []


def ensure_non_empty_list(value: list[T] | None) -> list[T] | list[None]:
    if not value:
        return [None]
    return value


def ensure_list_or_none(value: T | list[T] | None) -> list[T] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return [value]
    if len(value):
        return value
    return None
