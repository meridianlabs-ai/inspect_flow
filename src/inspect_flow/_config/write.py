from typing import Any

import yaml

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.args import MODEL_DUMP_ARGS


def _serialize_fallback(obj: Any) -> str:
    """Convert non-serializable objects to their string representation."""
    return repr(obj)


def config_to_yaml(spec: FlowSpec) -> str:
    return yaml.dump(
        spec.model_dump(**MODEL_DUMP_ARGS, fallback=_serialize_fallback),
        default_flow_style=False,
        sort_keys=False,
    )
