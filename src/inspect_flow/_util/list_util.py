from itertools import chain
from typing import TypeVar

T = TypeVar("T")


def flatten(list_of_lists: list[list[T]]) -> list[T]:
    return list(chain.from_iterable(list_of_lists))


def ensure_list(value: T | list[T] | None) -> list[T]:
    if isinstance(value, list):
        return value
    elif value is None:
        return []
    else:
        return [value]


def ensure_non_empty_list(value: T | list[T] | None) -> list[T] | list[T | None]:
    if isinstance(value, list):
        return value if len(value) else [None]
    else:
        return [value]


def ensure_list_or_none(value: T | list[T] | None) -> list[T] | None:
    if value is None:
        return None
    elif isinstance(value, list):
        return value if len(value) else None
    else:
        return [value]


def ensure_list_or_none(value: T | list[T] | None) -> list[T] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value]
