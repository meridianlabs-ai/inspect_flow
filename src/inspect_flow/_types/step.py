from collections.abc import Callable
from typing import TypeVar

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_name,
)

STEP_TYPE = "step"

F = TypeVar("F", bound=Callable[..., None])


def step(func: F) -> F:
    """Decorator to register a step function.

    Args:
        func: A function that takes a list of EvalLog objects and performs
            operations on them (tag, validate, copy, etc.).
    """
    name = registry_name(func, func.__name__)
    registry_add(
        func,
        RegistryInfo.model_construct(type=STEP_TYPE, name=name),
    )
    return func
