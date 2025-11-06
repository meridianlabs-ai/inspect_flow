import json
import sys
import traceback
from pathlib import Path

import click
import yaml
from pydantic_core import ValidationError, to_jsonable_python

from inspect_flow._types.dicts import FlowConfig
from inspect_flow._types.flow_types import FConfig
from inspect_flow._util.module_util import execute_file_and_get_last_result


def load_config(config_file: str) -> FConfig:
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    try:
        with open(config_path, "r") as f:
            if config_path.suffix == ".py":
                result = execute_file_and_get_last_result(config_path)
                if result is None:
                    raise ValueError(
                        f"No value returned from Python config file: {config_file}"
                    )
                if isinstance(result, FlowConfig):
                    result = FConfig.model_validate(to_jsonable_python(result))
                elif not isinstance(result, FConfig):
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
    except ValidationError as e:
        print_filtered_traceback(e, config_path)
        click.echo(e, err=True)
        sys.exit(1)

    return FConfig(**data)


def print_filtered_traceback(e: ValidationError, config_path: Path) -> None:
    tb = e.__traceback__
    stack_summary = traceback.extract_tb(tb)
    config_file = str(config_path.resolve())
    filtered_frames = [
        frame for frame in stack_summary if frame.filename in config_file
    ]
    traceback.print_list(filtered_frames)
