from typing import Any, Sequence, TypeGuard, TypeVar

_T = TypeVar("_T", int, str)


def sequence_to_list(
    value: Sequence[_T] | Any,
) -> list[_T] | Any:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return value
    return list(value)


def is_sequence(value: Any) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, str)
