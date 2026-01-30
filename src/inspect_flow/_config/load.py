import inspect
import json
import re
import traceback
from logging import getLogger
from pathlib import Path
from typing import Any, Callable, Sequence, TypeAlias, TypeVar

import yaml
from attr import dataclass, field
from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, exists, file, filesystem
from pydantic import BaseModel
from pydantic_core import ValidationError

from inspect_flow._config.defaults import apply_defaults
from inspect_flow._types.decorator import INSPECT_FLOW_AFTER_LOAD_ATTR
from inspect_flow._types.flow_types import FlowSpec, NotGiven, not_given
from inspect_flow._util.console import print, quantity
from inspect_flow._util.list_util import is_sequence
from inspect_flow._util.module_util import execute_file_and_get_last_result
from inspect_flow._util.path_util import absolute_path_relative_to
from inspect_flow._util.pydantic_util import model_dump

logger = getLogger(__file__)

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
    print(
        f"Loaded {quantity(len(spec.tasks or []), 'task')}",
        format="success",
    )
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
    spec = _apply_overrides(spec, options.overrides)
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
        if isinstance(include, FlowSpec):
            spec = _apply_include(spec, include)
            continue
        include_path = absolute_path_relative_to(include, base_dir=base_dir)
        included_spec = _load_spec_from_file(include_path, args, state)
        if included_spec is not None:
            spec = _apply_include(spec, included_spec)
    spec.includes = not_given
    return spec


class _SpecFormatMapMapping:
    """Mapping for spec config substitutions. Preserves missing keys."""

    def __init__(self, spec: FlowSpec) -> None:
        self.spec = spec

    def __getitem__(self, key: str, /) -> Any:
        if value := getattr(self.spec, key, None):
            # Convert Pydantic objects to dicts for nested access like {defaults[model][name]}
            if isinstance(value, BaseModel):
                return model_dump(value)
            return value
        return f"{{{key}}}"


def _apply_substitutions(spec: FlowSpec, base_dir: str) -> FlowSpec:
    """Apply any substitutions to the spec."""
    # Issue #266 must resolve the log dir before applying substitutions
    if spec.log_dir:
        spec.log_dir = _resolve_log_dir(spec, base_dir=base_dir)

    mapping = _SpecFormatMapMapping(spec)

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
        elif isinstance(obj, (list, tuple)):
            return [substitute_strings(item) for item in obj]
        elif isinstance(obj, BaseModel):
            # Process Pydantic objects by iterating over their fields
            updates = {}
            for field_name in type(obj).model_fields:
                value = getattr(obj, field_name)
                new_value = substitute_strings(value)
                if new_value is not value:
                    updates[field_name] = new_value
            if updates:
                return obj.model_copy(update=updates)
            return obj
        else:
            # Leave non-serializable objects (Task, Solver, etc.) unchanged
            return obj

    return substitute_strings(spec)


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

    log_dir = log_dir.rstrip(filesystem(log_dir).sep)
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
    print(f"Loading config: {config_file}")

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
    """Merge included_spec into spec, with spec's values taking precedence.

    Uses model_copy to preserve non-serializable objects like Task, Solver, etc.
    """
    return _merge_include_objects(spec, included_spec)


_T = TypeVar("_T", bound=BaseModel)


def _merge_include_objects(spec: _T, included: _T) -> _T:
    """Recursively merge two BaseModel objects, with spec taking precedence."""
    updates: dict[str, Any] = {}

    for field_name in type(spec).model_fields:
        spec_value = getattr(spec, field_name)
        included_value = getattr(included, field_name)

        if isinstance(included_value, NotGiven):
            pass
        elif isinstance(spec_value, NotGiven):
            updates[field_name] = included_value
        elif isinstance(spec_value, BaseModel) and isinstance(
            included_value, BaseModel
        ):
            # recursively merge pydantic objects
            merged = _merge_include_objects(spec_value, included_value)
            updates[field_name] = merged
        elif isinstance(spec_value, dict) and isinstance(included_value, dict):
            # merge dicts, with spec taking precedence
            merged_dict = {**included_value, **spec_value}
            updates[field_name] = merged_dict
        elif is_sequence(spec_value) and is_sequence(included_value):
            # For lists, concatenate with included first, avoiding duplicates
            merged_list = list(included_value) + [
                item for item in spec_value if item not in included_value
            ]
            updates[field_name] = merged_list
        # Otherwise keep spec's value (no update needed)

    if updates:
        return spec.model_copy(update=updates)
    return spec


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


def _override_value(keys: list[str], value: str) -> Any:
    if not keys:
        return _maybe_json(value)
    result: dict[str, Any] = {}
    obj = result
    for key in keys[:-1]:
        obj = obj.setdefault(key, {})
    obj[keys[-1]] = _maybe_json(value)
    return result


def _apply_override_to_list(
    obj: Sequence[Any], keys: list[str], value: str
) -> Sequence[Any]:
    override_value = _override_value(keys, value)
    if isinstance(override_value, list):
        # Treat override of a list with a list as full replacement
        return override_value
    elif override_value not in obj:
        # Append to list
        return list(obj) + [override_value]
    return obj


def _update_value(current_value: Any, keys: list[str], value: str) -> Any:
    if is_sequence(current_value):
        return _apply_override_to_list(current_value, keys, value)
    elif not keys:
        return _maybe_json(value)
    elif isinstance(current_value, BaseModel):
        return _apply_override_to_model(current_value, keys, value)
    elif isinstance(current_value, dict):
        return _apply_override_to_dict(current_value, keys, value)
    else:
        return _override_value(keys, value)


def _apply_override_to_model(obj: _T, keys: list[str], value: str) -> _T:
    current_value = getattr(obj, keys[0], not_given)
    if isinstance(current_value, NotGiven):
        # To support nested pydantic objects, need to figure out the field type for the override.
        # Use model_validate to do that.
        override_model = type(obj).model_validate(
            _override_value(keys, value), extra="forbid"
        )
        update_value = getattr(override_model, keys[0])
    else:
        update_value = _update_value(current_value, keys[1:], value)
    return obj.model_copy(update={keys[0]: update_value})


def _apply_override_to_dict(
    obj: dict[str, Any], keys: list[str], value: str
) -> dict[str, Any]:
    current_value = obj.get(keys[0], None)
    update_value = _update_value(current_value, keys[1:], value)
    return {**obj, keys[0]: update_value}


def _apply_overrides(spec: FlowSpec, overrides: list[str]) -> FlowSpec:
    for override in overrides:
        key_path, value = override.split("=", 1)
        keys = key_path.split(".")
        spec = _apply_override_to_model(spec, keys, value)
    return spec


def _print_filtered_traceback(e: ValidationError, config_file: str) -> None:
    tb = e.__traceback__
    stack_summary = traceback.extract_tb(tb)
    filtered_frames = [
        frame for frame in stack_summary if frame.filename in config_file
    ]
    for item in traceback.format_list(filtered_frames):
        logger.error(item)
