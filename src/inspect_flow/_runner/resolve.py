import sys
from typing import TypeAlias, TypeVar

from inspect_ai.model import Model
from pydantic import BaseModel

from inspect_flow._config.defaults import apply_defaults
from inspect_flow._types.flow_types import (
    FlowSpec,
    not_given,
)

ModelRoles: TypeAlias = dict[str, str | Model]

_T = TypeVar("_T", bound=BaseModel)


def _resolve_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def resolve_spec(spec: FlowSpec, base_dir: str) -> FlowSpec:
    spec = apply_defaults(spec)

    return spec.model_copy(
        update={
            "defaults": not_given,
            "python_version": _resolve_python_version(),
        }
    )
