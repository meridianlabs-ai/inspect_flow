from typing import Any

from pydantic import BaseModel


def _serialize_fallback(obj: Any) -> str:
    """Convert non-serializable objects to their string representation."""
    return repr(obj)


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
