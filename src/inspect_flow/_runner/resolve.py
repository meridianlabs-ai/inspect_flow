import sys

from inspect_flow._config.defaults import apply_defaults
from inspect_flow._types.flow_types import (
    FlowSpec,
    not_given,
)


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
