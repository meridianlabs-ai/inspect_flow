from typing import Any, Sequence, TypeVar

from typing_extensions import TypeIs

_T = TypeVar("_T", int, str)


def sequence_to_list(
    value: Sequence[_T] | Any,
) -> list[_T] | Any:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return value
    return list(value)


# TypeIs (not TypeGuard) so the else branch narrows too. Caveat: str is a
# runtime Sequence that this predicate rejects, so in an else branch checkers
# drop str from Sequence-typed unions even though a str can still flow there —
# else branches must keep handling str as a scalar.
def is_sequence(value: Any) -> TypeIs[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, str)
