from collections.abc import Callable
from typing import Concatenate, ParamSpec

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_name,
)
from inspect_ai.log import EvalLog

STEP_TYPE = "step"

P = ParamSpec("P")
StepFunction = Callable[Concatenate[list[EvalLog], P], list[EvalLog]]


def step(func: StepFunction[P]) -> StepFunction[P]:
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
