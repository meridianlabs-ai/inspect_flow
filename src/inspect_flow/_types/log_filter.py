from collections.abc import Callable

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_lookup,
    registry_name,
)
from inspect_ai.log import EvalLog

from inspect_flow._types.flow_types import LogFilter

LOG_FILTER_TYPE = "log_filter"


def log_filter(func: Callable[[EvalLog], bool]) -> Callable[[EvalLog], bool]:
    """Decorator to register a log filter function.

    Args:
        func: A function that takes an EvalLog and returns True to include.
    """
    name = registry_name(func, func.__name__)
    registry_add(
        func,
        RegistryInfo(type=LOG_FILTER_TYPE, name=name),  # type: ignore[arg-type]
    )
    return func


def resolve_log_filter(filter: LogFilter | str | None) -> LogFilter | None:
    """Resolve a log filter from a callable, registered name, or None."""
    if filter is None or callable(filter):
        return filter
    resolved = registry_lookup(LOG_FILTER_TYPE, filter)  # type: ignore[arg-type]
    if resolved is None:
        raise ValueError(f"Log filter '{filter}' not found in registry.")
    return resolved  # type: ignore[return-value]
