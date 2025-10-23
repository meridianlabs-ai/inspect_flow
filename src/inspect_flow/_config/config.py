import json
from pathlib import Path

import yaml

from inspect_flow._types.flow_types import FlowConfig
from inspect_flow._util.module_util import execute_file_and_get_last_result


def load_config(config_file: str) -> FlowConfig:
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_path, "r") as f:
        if config_path.suffix == ".py":
            result = execute_file_and_get_last_result(config_path)
            if result is None:
                raise ValueError(
                    f"No value returned from Python config file: {config_file}"
                )
            if not isinstance(result, FlowConfig):
                raise TypeError(
                    f"Expected FlowConfig from Python config file, got {type(result)}"
                )
            return result
        elif config_path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(f)
        elif config_path.suffix == ".json":
            data = json.load(f)
        else:
            raise ValueError(
                f"Unsupported config file format: {config_path.suffix}. "
                "Supported formats: .yaml, .yml, .json"
            )

    return FlowConfig(**data)
