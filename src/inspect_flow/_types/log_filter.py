from collections.abc import Callable, Sequence
from pathlib import Path

from inspect_ai._util.module import load_module
from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_find,
    registry_lookup,
    registry_name,
)
from inspect_ai.log import EvalLog

from inspect_flow._types.flow_types import LogFilter
from inspect_flow._util.path_util import absolute_path_relative_to, find_auto_includes

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


def resolve_log_filter(
    filter: LogFilter | str | Sequence[LogFilter | str] | None,
    base_dir: str | None = None,
) -> LogFilter | None:
    """Resolve a log filter from a callable, registered name, sequence, or None.

    Args:
        filter: A callable, registered name, "file.py@name" string, a sequence of
            any of the above (all must pass), or None.
        base_dir: Base directory for resolving relative file paths in
            "file.py@name" syntax. Defaults to the current working directory.
    """
    if isinstance(filter, Sequence) and not isinstance(filter, str):
        filters = [
            f
            for f in (resolve_log_filter(f, base_dir) for f in filter)
            if f is not None
        ]
        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return lambda log: all(f(log) for f in filters)
    if filter is None or callable(filter):
        return filter
    if "@" in filter:
        file_path, name = filter.rsplit("@", 1)
        if base_dir:
            file_path = absolute_path_relative_to(file_path, base_dir)
        load_module(Path(file_path))
        filter = name
    resolved = registry_lookup(LOG_FILTER_TYPE, filter)  # type: ignore[arg-type]
    if resolved is None:
        # Load _flow.py files from cwd and parent dirs, which may register
        # @log_filter decorators.
        for flow_file in find_auto_includes(str(Path.cwd())):
            load_module(Path(flow_file))
        resolved = registry_lookup(LOG_FILTER_TYPE, filter)  # type: ignore[arg-type]
    if resolved is None:
        # Bare names may be registered with a package namespace prefix
        # (e.g., "only_success" registered as "local_eval/only_success").
        # registry_find also calls ensure_entry_points() if nothing matches.
        matches = registry_find(
            lambda info: (
                info.type == LOG_FILTER_TYPE and info.name.endswith(f"/{filter}")
            )
        )
        if len(matches) == 1:
            resolved = matches[0]
        elif len(matches) > 1:
            names = [registry_name(m, "") for m in matches]
            raise ValueError(
                f"Multiple log filters match '{filter}': {names}. "
                "Use a fully qualified name."
            )
    if resolved is None:
        raise ValueError(f"Log filter '{filter}' not found in registry.")
    return resolved  # type: ignore[return-value]
