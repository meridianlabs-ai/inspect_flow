import inspect
import json
import re
import traceback
from logging import getLogger
from pathlib import Path
from typing import Any, Callable, TypeAlias

import yaml
from attr import dataclass, field
from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, exists, file
from pydantic_core import ValidationError

from inspect_flow._config.defaults import apply_defaults
from inspect_flow._types.decorator import INSPECT_FLOW_AFTER_LOAD_ATTR
from inspect_flow._types.flow_types import FlowSpec, not_given
from inspect_flow._util.args import MODEL_DUMP_ARGS
from inspect_flow._util.constants import PKG_NAME
from inspect_flow._util.module_util import execute_file_and_get_last_result
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(PKG_NAME)

AUTO_INCLUDE_FILENAME = "_flow.py"


@dataclass
class ConfigOptions:
    overrides: list[str] = field(factory=list)
    args: dict[str, Any] = field(factory=dict)


@dataclass
class LoadState:
    files_to_specs: dict[str, FlowSpec | None] = field(factory=dict)
    after_flow_spec_loaded_funcs: list[Callable] = field(factory=list)


def int_load_spec(file: str, options: ConfigOptions) -> FlowSpec:
    state = LoadState()
    file = absolute_file_path(file)
    spec = _load_spec_from_file(file, args=options.args, state=state)
    if spec is None:
        raise ValueError(f"No value returned from Python config file: {file}")

    base_dir = Path(file).parent.as_posix()
    spec = expand_spec(spec, base_dir=base_dir, options=options)
    return spec


def expand_spec(
    spec: FlowSpec, base_dir: str, options: ConfigOptions | None = None
) -> FlowSpec:
    options = options or ConfigOptions()
    state = LoadState()
    spec = _expand_includes(
        spec,
        state,
        base_dir=base_dir,
    )
    spec = _apply_auto_includes(spec, base_dir=base_dir, options=options, state=state)
    if options.overrides:
        return _apply_overrides(spec, options.overrides)
    spec = _apply_substitutions(spec, base_dir=base_dir)
    spec = apply_defaults(spec)
    _after_flow_spec_loaded(spec, state)
    return spec


def _after_flow_spec_loaded(spec: FlowSpec, state: LoadState) -> None:
    """Run any registered after_flow_spec_loaded functions."""
    for func in state.after_flow_spec_loaded_funcs:
        sig = inspect.signature(func)
        filtered_args = {
            k: v
            for k, v in {"spec": spec, "files": state.files_to_specs.keys()}.items()
            if k in sig.parameters
        }
        func(**filtered_args)


def _expand_includes(
    spec: FlowSpec,
    state: LoadState,
    base_dir: str = "",
    args: dict[str, Any] | None = None,
) -> FlowSpec:
    """Apply includes in the spec config."""
    if args is None:
        args = dict()
    for include in spec.includes or []:
        include_path = absolute_path_relative_to(include, base_dir=base_dir)
        included_spec = _load_spec_from_file(include_path, args, state)
        if included_spec is not None:
            spec = _apply_include(spec, included_spec)
    spec.includes = not_given
    return spec


class _SpecFormatMapMapping:
    """Mapping for spec config substitutions. Preserves missing keys."""

    def __init__(self, dict: dict[str, Any]) -> None:
        self.dict = dict

    def __getitem__(self, key: str, /) -> Any:
        return self.dict.get(key, f"{{{key}}}")


def _apply_substitutions(spec: FlowSpec, base_dir: str) -> FlowSpec:
    """Apply any substitutions to the spec."""
    # Issue #266 must resolve the log dir before applying substitutions
    if spec.log_dir:
        spec.log_dir = _resolve_log_dir(spec, base_dir=base_dir)

    spec_dict = spec.model_dump(**MODEL_DUMP_ARGS)
    mapping = _SpecFormatMapMapping(spec_dict)

    # Recursively apply substitutions to all string fields
    def substitute_strings(obj: Any) -> Any:
        if isinstance(obj, str):
            last = obj
            new = obj.format_map(mapping)
            # Repeat until no more substitutions occur
            while new != last:
                if obj in new:
                    raise ValueError(
                        f"Circular substitution detected for string: {obj}"
                    )
                last = new
                new = last.format_map(mapping)
            return new
        elif isinstance(obj, dict):
            return {k: substitute_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute_strings(item) for item in obj]
        else:
            return obj

    substituted_dict = substitute_strings(spec_dict)
    return FlowSpec.model_validate(substituted_dict, extra="forbid")


def _resolve_log_dir(spec: FlowSpec, base_dir: str) -> str:
    assert spec.log_dir
    if not spec.log_dir_create_unique:
        return spec.log_dir
    absolute_log_dir = absolute_path_relative_to(spec.log_dir, base_dir=base_dir)
    already_absolute = absolute_log_dir == spec.log_dir
    unique_absolute_log_dir = _log_dir_create_unique(absolute_log_dir)
    if already_absolute:
        return unique_absolute_log_dir
    try:
        unique_relative_log_dir = str(
            Path(unique_absolute_log_dir).relative_to(base_dir)
        )
    except ValueError:
        return unique_absolute_log_dir
    return unique_relative_log_dir


def _log_dir_create_unique(log_dir: str) -> str:
    if not exists(log_dir):
        return log_dir

    # Check if log_dir ends with _<number>
    match = re.match(r"^(.+)_(\d+)$", log_dir)
    if match:
        base_log_dir = match.group(1)
        suffix = int(match.group(2)) + 1  # Start from next suffix
    else:
        base_log_dir = log_dir
        suffix = 1

    # Find the next available directory
    current_dir = f"{base_log_dir}_{suffix}"
    while exists(current_dir):
        suffix += 1
        current_dir = f"{base_log_dir}_{suffix}"
    return current_dir


def _load_spec_from_file(
    config_file: str, args: dict[str, Any], state: LoadState
) -> FlowSpec | None:
    config_path = Path(absolute_file_path(config_file))
    logger.info(f"Loading config file: {config_path.as_posix()}")

    try:
        with file(config_file, "r") as f:
            if config_path.suffix == ".py":
                spec, globals = execute_file_and_get_last_result(config_file, args=args)
                if spec is None or isinstance(spec, FlowSpec):
                    state.files_to_specs[config_file] = spec
                    state.after_flow_spec_loaded_funcs.extend(
                        [
                            v
                            for v in globals.values()
                            if hasattr(v, INSPECT_FLOW_AFTER_LOAD_ATTR)
                        ]
                    )

                else:
                    raise TypeError(
                        f"Expected FlowSpec from Python config file, got {type(spec)}"
                    )
            else:
                if config_path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    raise ValueError(
                        f"Unsupported config file extension: {config_path.suffix}. "
                        "Supported extensions: .py, .yaml, .yml"
                    )
                spec = FlowSpec.model_validate(data, extra="forbid")
    except ValidationError as e:
        _print_filtered_traceback(e, config_file)
        logger.error(e)
        e._flow_handled = True  # type: ignore
        raise

    if spec:
        return _expand_includes(
            spec, state, base_dir=config_path.parent.as_posix(), args=args
        )
    return None


def _apply_include(spec: FlowSpec, included_spec: FlowSpec) -> FlowSpec:
    spec_dict = spec.model_dump(**MODEL_DUMP_ARGS)
    include_dict = included_spec.model_dump(**MODEL_DUMP_ARGS)
    merged_dict = _deep_merge_include(include_dict, spec_dict)
    return FlowSpec.model_validate(merged_dict, extra="forbid")


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
                result[k] = base_v + [item for item in override_v if item not in base_v]
            else:
                result[k] = override_v
    return result


def _apply_auto_includes(
    spec: FlowSpec, base_dir: str, options: ConfigOptions, state: LoadState
) -> FlowSpec:
    absolute_path = absolute_file_path(base_dir)
    protocol, path = split_protocol(absolute_path)

    parent_dir = Path(base_dir)
    auto_include_count = 0
    while True:
        auto_file = str(parent_dir / AUTO_INCLUDE_FILENAME)
        if protocol:
            auto_file = f"{protocol}://{auto_file}"
        if exists(auto_file):
            auto_spec = _load_spec_from_file(auto_file, args=options.args, state=state)
            if (auto_include_count := auto_include_count + 1) > 1:
                logger.warning(
                    f"Applying multiple {AUTO_INCLUDE_FILENAME}. #{auto_include_count}: {auto_file}"
                )
            if auto_spec:
                spec = _apply_include(spec, auto_spec)
        if parent_dir.parent == parent_dir:
            break
        parent_dir = parent_dir.parent
    return spec


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


def _apply_overrides(spec: FlowSpec, overrides: list[str]) -> FlowSpec:
    overrides_dict = _overrides_to_dict(overrides)
    base_dict = spec.model_dump(**MODEL_DUMP_ARGS)
    merged_dict = _deep_merge_override(base_dict, overrides_dict)
    return FlowSpec.model_validate(merged_dict, extra="forbid")


def _print_filtered_traceback(e: ValidationError, config_file: str) -> None:
    tb = e.__traceback__
    stack_summary = traceback.extract_tb(tb)
    filtered_frames = [
        frame for frame in stack_summary if frame.filename in config_file
    ]
    for item in traceback.format_list(filtered_frames):
        logger.error(item)
