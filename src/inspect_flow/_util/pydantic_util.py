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

    A registry object serializes to its registry name. Any other callable
    serializes as `<file>@<name>`, which only resolves if the callable is a
    module-level function: lambdas, nested functions, methods, classes,
    partials, and callable objects either have no `__code__` (crashing
    `callable_name`) or name something that cannot be imported back.
    """
    if not callable(value):
        return False
    if is_registry_object(value):
        return True
    return (
        getattr(value, "__code__", None) is not None
        and value.__name__ != "<lambda>"
        and getattr(value, "__qualname__", value.__name__) == value.__name__
    )


def survives_round_trip(obj: Any) -> bool:
    """Whether an object that reaches the dump fallback survives reloading.

    Serializing is only half a round trip. A callable that `callable_name`
    can name again is recreated by the loader, but a registry dict reloads as
    a plain dict rather than the object it came from, and everything else
    reloads as the text of its `repr`.
    """
    return is_nameable_callable(registry_value(obj))


def _serialize_fallback(obj: Any) -> Any:
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
    "fallback": _serialize_fallback,
}


def model_dump(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
    """Dump a Pydantic model to a dictionary using standard settings."""
    return obj.model_dump(**(MODEL_DUMP_ARGS | kwargs))
