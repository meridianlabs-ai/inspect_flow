from collections.abc import Callable
from typing import Any

from inspect_ai._util.registry import is_registry_object, registry_info, registry_value
from pydantic import BaseModel


def callable_name(value: Callable[..., Any]) -> str:
    if is_registry_object(value):
        info = registry_info(value)
        return f"{info.name}"
    else:
        return f"{value.__code__.co_filename}@{value.__name__}"


def is_nameable_callable(value: Any) -> bool:
    """Whether `callable_name` can produce a reference that resolves again.

    Only a registry object can. Every resolver that consumes `callable_name`'s
    output finishes with a registry lookup — task/model/scorer/solver/agent
    factories via inspect's loader, log filters via `_types.log_filter` — so
    the `<file>@<name>` form it emits for a plain callable names the file to
    import but then fails to find the name. An unregistered function is
    therefore no more portable than a lambda; it just fails later, in the
    child, with "Task named '...' not found".
    """
    return callable(value) and is_registry_object(value)


def serializes_to_registry_dict(obj: Any) -> bool:
    """Whether an object serializes to a registry dict.

    Such a dict only becomes the object again where the loader passes it
    through `registry_kwargs`; elsewhere it reloads as a plain dict.
    """
    return isinstance(registry_value(obj), dict)


def survives_round_trip(obj: Any) -> bool:
    """Whether an object that reaches the dump fallback survives reloading.

    Serializing is only half a round trip. A callable that `callable_name`
    can name again is recreated by the loader; everything else reloads as the
    text of its `repr` or as a plain dict. See `serializes_to_registry_dict`
    for the values that survive only in re-inflated positions.
    """
    return is_nameable_callable(registry_value(obj))


def serialize_fallback(obj: Any) -> Any:
    """Convert non-serializable objects to their string representation.

    Uses JSON format for dicts to avoid quote escaping issues in YAML output.
    """
    value = registry_value(obj)
    if isinstance(value, dict):
        return value
    if callable(value):
        return callable_name(value)
    return repr(value)


MODEL_DUMP_ARGS = {
    "mode": "json",
    "exclude_unset": True,
    "exclude_defaults": True,
    # do not exclude_none, as for NotGiven fields they are significant
    "fallback": serialize_fallback,
}


def model_dump(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
    """Dump a Pydantic model to a dictionary using standard settings."""
    return obj.model_dump(**(MODEL_DUMP_ARGS | kwargs))
