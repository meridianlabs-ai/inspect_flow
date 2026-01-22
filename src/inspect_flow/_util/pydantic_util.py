from typing import Any, Callable

from inspect_ai._util.registry import is_registry_object, registry_info, registry_value
from pydantic import BaseModel


def callable_name(value: Callable) -> str:
    if is_registry_object(value):
        info = registry_info(value)
        return f"{info.name}"
    else:
        return f"{value.__code__.co_filename}@{value.__name__}"


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
