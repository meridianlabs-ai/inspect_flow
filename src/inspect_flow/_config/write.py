import yaml

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.args import MODEL_DUMP_ARGS


def config_to_yaml(spec: FlowSpec) -> str:
    return yaml.dump(
        spec.model_dump(**MODEL_DUMP_ARGS),
        default_flow_style=False,
        sort_keys=False,
    )
