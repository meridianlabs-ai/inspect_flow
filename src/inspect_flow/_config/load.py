import json
import sys
import traceback
from pathlib import Path
from typing import Any, TypeAlias

import click
import yaml
from attr import dataclass
from inspect_ai._util.file import file
from pydantic_core import ValidationError, to_jsonable_python

from inspect_flow._types.flow_types import FlowConfig
from inspect_flow._util.module_util import execute_file_and_get_last_result
from inspect_flow._util.path_util import set_config_path_env_var


@dataclass
class ConfigOptions:
    """Options for loading a configuration file.

    Attributes:
        overrides: A list of configuration overrides in the form of "key1.key2=value" strings.
        flow_vars: A dictionary available as '__flow_vars__' when loading the config.
    """

    overrides: list[str] = []
    flow_vars: dict[str, str] = {}


def load_config(
    config_file: str, config_options: ConfigOptions | None = None
) -> FlowConfig:
    """Load a configuration file and apply any overrides.

    Args:
        config_file: The path to the configuration file.
        config_options: Options for loading the config.
    """
    config_options = config_options or ConfigOptions()
    config = _load_config_from_file(config_file, config_options.flow_vars)
    set_config_path_env_var(config_file)
    if config_options.overrides:
        return _apply_overrides(config, config_options.overrides)
    return config


def _load_config_from_file(config_file: str, flow_vars: dict[str, str]) -> FlowConfig:
    config_path = Path(config_file)

    try:
        with file(config_file, "r") as f:
            if config_path.suffix == ".py":
                result = execute_file_and_get_last_result(config_file, flow_vars)
                if result is None:
                    raise ValueError(
                        f"No value returned from Python config file: {config_file}"
                    )
                if isinstance(result, FlowConfig):
                    result = FlowConfig.model_validate(to_jsonable_python(result))
                elif not isinstance(result, FlowConfig):
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
        _print_filtered_traceback(e, config_file)
        click.echo(e, err=True)
        sys.exit(1)

    return FlowConfig(**data)


def _maybe_json(value: str) -> Any:
    try:
        print(f"Trying to parse JSON value: {value}")
        return json.loads(value)
    except json.JSONDecodeError:
        return value


_OverrideDict: TypeAlias = dict[str, "str | _OverrideDict"]


def _overrides_to_dict(overrides: list[str]) -> _OverrideDict:
    result: dict[str, Any] = {}
    for override in overrides:
        key_path, value = override.split("=", 1)
        keys = key_path.split(".")
        obj = result
        for key in keys[:-1]:
            obj = obj.setdefault(key, {})
        obj[keys[-1]] = value
    return result


def _deep_merge(base: dict[str, Any], override: _OverrideDict) -> dict[str, Any]:
    for k, v in override.items():
        base_v = base.get(k)
        if isinstance(v, dict):
            if isinstance(base_v, dict):
                _deep_merge(base_v, v)
            else:
                base[k] = v
        elif isinstance(base_v, list):
            json_v = _maybe_json(v)
            if isinstance(json_v, list):
                base[k] = json_v
            else:
                base_v.append(v)
        else:
            json_v = _maybe_json(v)
            if isinstance(json_v, list | dict):
                base[k] = json_v
            else:
                base[k] = v
    return base


def _apply_overrides(config: FlowConfig, overrides: list[str]) -> FlowConfig:
    overrides_dict = _overrides_to_dict(overrides)
    base_dict = config.model_dump(mode="json", exclude_none=True)
    merged_dict = _deep_merge(base_dict, overrides_dict)
    return FlowConfig.model_validate(merged_dict)


def _print_filtered_traceback(e: ValidationError, config_file: str) -> None:
    tb = e.__traceback__
    stack_summary = traceback.extract_tb(tb)
    filtered_frames = [
        frame for frame in stack_summary if frame.filename in config_file
    ]
    traceback.print_list(filtered_frames)
