import json
import sys
import traceback
from pathlib import Path
from typing import Any, TypeAlias

import click
import yaml
from inspect_ai._util.file import exists, file
from pydantic_core import ValidationError
from typing_extensions import TypedDict, Unpack

from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.module_util import execute_file_and_get_last_result
from inspect_flow._util.path_util import (
    absolute_path_relative_to,
    set_config_path_env_var,
)

AUTO_INCLUDE_FILENAME = "_flow.py"


class ConfigOptions(TypedDict, total=False):
    """Options for loading a configuration file.

    Attributes:
        overrides: A list of configuration overrides in the form of "key1.key2=value" strings.
        flow_vars: A dictionary available as '__flow_vars__' when loading the config.
    """

    overrides: list[str]
    flow_vars: dict[str, str]


def load_config(config_file: str, **kwargs: Unpack[ConfigOptions]) -> FlowJob:
    """Load a configuration file and apply any overrides.

    Args:
        config_file: The path to the configuration file.
        **kwargs: Configuration options. See ConfigOptions for available parameters.
    """
    config_options = ConfigOptions(**kwargs)
    set_config_path_env_var(config_file)
    job = _load_config_from_file(config_file, config_options.get("flow_vars", {}))
    job = _apply_auto_includes(job, config_file, config_options)

    overrides = config_options.get("overrides", [])
    if overrides:
        return _apply_overrides(job, overrides)
    return job


def expand_includes(
    job: FlowJob, base_path: str = "", flow_vars: dict[str, str] | None = None
) -> FlowJob:
    """Apply includes in the job config."""
    if flow_vars is None:
        flow_vars = dict()
    for include in job.includes or []:
        path = include if isinstance(include, str) else include.config_file_path
        if not path:
            raise ValueError("Include must have a config_file_path set.")
        include_path = absolute_path_relative_to(path, base_path)
        included_job = _load_config_from_file(include_path, flow_vars)
        job = _apply_include(job, included_job)
    job.includes = None
    return job


def _load_config_from_file(config_file: str, flow_vars: dict[str, str]) -> FlowJob:
    config_path = Path(config_file)

    try:
        with file(config_file, "r") as f:
            if config_path.suffix == ".py":
                job = execute_file_and_get_last_result(config_file, flow_vars)
                if job is None:
                    raise ValueError(
                        f"No value returned from Python config file: {config_file}"
                    )
                if not isinstance(job, FlowJob):
                    raise TypeError(
                        f"Expected FlowJob from Python config file, got {type(job)}"
                    )
            else:
                if config_path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif config_path.suffix == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(
                        f"Unsupported config file format: {config_path.suffix}. "
                        "Supported formats: .py, .yaml, .yml, .json"
                    )
                job = FlowJob.model_validate(data)
    except ValidationError as e:
        _print_filtered_traceback(e, config_file)
        click.echo(e, err=True)
        sys.exit(1)

    return expand_includes(job, str(config_path.parent), flow_vars)


def _apply_include(job: FlowJob, included_job: FlowJob) -> FlowJob:
    job_dict = job.model_dump(mode="json", exclude_none=True)
    include_dict = included_job.model_dump(mode="json", exclude_none=True)
    merged_dict = _deep_merge_include(include_dict, job_dict)
    return FlowJob.model_validate(merged_dict)


def _deep_merge_include(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    result = base.copy()
    for k, override_v in override.items():
        if k not in result:
            result[k] = override_v
        else:
            base_v = result[k]
            if isinstance(override_v, dict) and isinstance(base_v, dict):
                result[k] = _deep_merge_include(base_v, override_v)
            elif isinstance(override_v, list) and isinstance(base_v, list):
                result[k] = base_v + override_v
            else:
                result[k] = override_v
    return result


def _apply_auto_includes(
    job: FlowJob, config_file: str, config_options: ConfigOptions
) -> FlowJob:
    parent_dir = Path(config_file).parent
    while True:
        auto_file = str(parent_dir / AUTO_INCLUDE_FILENAME)
        if exists(auto_file):
            auto_job = _load_config_from_file(
                auto_file, config_options.get("flow_vars", {})
            )
            job = _apply_include(job, auto_job)
        if parent_dir.parent == parent_dir:
            break
        parent_dir = parent_dir.parent
    return job


def _maybe_json(value: str) -> Any:
    try:
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


def _deep_merge_override(
    base: dict[str, Any], override: _OverrideDict
) -> dict[str, Any]:
    for k, v in override.items():
        base_v = base.get(k)
        if isinstance(v, dict):
            if isinstance(base_v, dict):
                _deep_merge_override(base_v, v)
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


def _apply_overrides(config: FlowJob, overrides: list[str]) -> FlowJob:
    overrides_dict = _overrides_to_dict(overrides)
    base_dict = config.model_dump(mode="json", exclude_none=True)
    merged_dict = _deep_merge_override(base_dict, overrides_dict)
    return FlowJob.model_validate(merged_dict)


def _print_filtered_traceback(e: ValidationError, config_file: str) -> None:
    tb = e.__traceback__
    stack_summary = traceback.extract_tb(tb)
    filtered_frames = [
        frame for frame in stack_summary if frame.filename in config_file
    ]
    traceback.print_list(filtered_frames)
