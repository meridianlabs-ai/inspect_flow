from typing import Any, Mapping, TypeVar

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
)
from inspect_flow._util.args import MODEL_DUMP_ARGS


def to_dict(input: Any) -> dict[str, Any]:
    if isinstance(input, Mapping):
        return dict(input)
    if isinstance(input, BaseModel):
        return input.model_dump(**MODEL_DUMP_ARGS)
    return to_jsonable_python(input, exclude_none=True)


def _merge_dicts(base_dict: dict[str, Any], add_dict: dict[str, Any]) -> dict[str, Any]:
    return base_dict | add_dict


def _merge(base: Any, add: Any) -> dict[str, Any]:
    return _merge_dicts(to_dict(base), to_dict(add))


# Note that current recursive merges do not go deeper than one level
_RECURSIVE_KEYS = {"config", "flow_metadata"}


_T = TypeVar("_T", FlowAgent, GenerateConfig, FlowModel, FlowSolver, FlowTask)


def merge_recursive(
    base: _T | Mapping[str, Any],
    add: _T | Mapping[str, Any],
) -> dict[str, Any]:
    base_dict = to_dict(base)
    add_dict = to_dict(add)
    result = _merge_dicts(base_dict, add_dict)
    for key in _RECURSIVE_KEYS:
        if (add_value := add_dict.get(key)) and (base_value := base_dict.get(key)):
            result[key] = _merge(base_value, add_value)
    return result


def merge(base: _T, add: _T) -> _T:
    """Merge two flow objects.

    Args:
        base: The base object.
        add: The object to merge into the base. Values in this object
            will override those in the base.
    """
    return type(base).model_validate(merge_recursive(base, add), extra="forbid")
