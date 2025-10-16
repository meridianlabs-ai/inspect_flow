import json
from pathlib import Path

import yaml

from inspect_flow._types.types import FlowConfig
from inspect_flow._util.module_util import get_module_from_file


def load_config(config_file: str) -> FlowConfig:
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_path, "r") as f:
        if config_path.suffix == ".py":
            module = get_module_from_file(config_path)
            return module.flow_config()
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
