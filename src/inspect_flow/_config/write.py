import yaml

from inspect_flow._types.flow_types import FlowConfig


def config_to_yaml(config: FlowConfig) -> str:
    return yaml.dump(
        config.model_dump(
            mode="json",
            exclude_unset=True,
            exclude_defaults=True,
            exclude_none=True,
        ),
        default_flow_style=False,
        sort_keys=False,
    )
