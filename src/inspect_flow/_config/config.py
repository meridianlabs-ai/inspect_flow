import json
from pathlib import Path

import yaml

from inspect_flow._types.types import FlowConfig


def load_config(config_file: str) -> FlowConfig:
    """Load configuration from a YAML or JSON file.

    Args:
        config_file: Path to the configuration file

    Returns:
        Config: Parsed configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If file format is not supported
    """
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_path, "r") as f:
        if config_path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(f)
        elif config_path.suffix == ".json":
            data = json.load(f)
        else:
            raise ValueError(
                f"Unsupported config file format: {config_path.suffix}. "
                "Supported formats: .yaml, .yml, .json"
            )

    return FlowConfig(**data)
