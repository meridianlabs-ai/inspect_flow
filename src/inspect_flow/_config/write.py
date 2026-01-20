import yaml

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.pydantic_util import model_dump


def config_to_yaml(spec: FlowSpec) -> str:
    return yaml.dump(
        model_dump(spec),
        default_flow_style=False,
        sort_keys=False,
    )
