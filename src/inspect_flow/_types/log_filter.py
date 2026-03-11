from collections.abc import Callable
from pathlib import Path

from inspect_ai._util.module import load_module
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
    # model_construct bypasses Pydantic validation of RegistryType literal,
    # since "log_filter" is not in inspect_ai's RegistryType enum.
    registry_add(
        func,
        RegistryInfo.model_construct(type=LOG_FILTER_TYPE, name=name),
    )
    return func


def resolve_log_filter(filter: LogFilter | str | None) -> LogFilter | None:
    """Resolve a log filter from a callable, registered name, or None.

    Accepts:
        - None or a callable: returned as-is
        - "name": looked up in the registry
        - "file.py@name": loads the file (executing @log_filter decorators),
          then looks up the name in the registry
    """
    if filter is None or callable(filter):
        return filter
    if "@" in filter:
        file_path, name = filter.rsplit("@", 1)
        load_module(Path(file_path))
        filter = name
    resolved = registry_lookup(LOG_FILTER_TYPE, filter)  # type: ignore[arg-type]
    if resolved is None:
        raise ValueError(f"Log filter '{filter}' not found in registry.")
    return resolved  # type: ignore[return-value]
