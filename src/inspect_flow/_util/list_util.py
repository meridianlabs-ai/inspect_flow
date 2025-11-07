from typing import TypeVar

T = TypeVar("T")


def ensure_list_or_none(value: T | list[T] | None) -> list[T] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return [value]
    if len(value):
        return value
    return None
