from typing import Any, Mapping, TypeAlias

from pydantic_core import to_jsonable_python

from inspect_flow._types.flow_types import (
    FAgent,
    FGenerateConfig,
    FModel,
    FSolver,
    FTask,
)
from inspect_flow._types.generated import (
    FlowAgent,
    FlowAgentDict,
    FlowGenerateConfig,
    FlowGenerateConfigDict,
    FlowModel,
    FlowModelDict,
    FlowSolver,
    FlowSolverDict,
    FlowTask,
    FlowTaskDict,
)

AgentType: TypeAlias = FAgent | FlowAgent | FlowAgentDict
GenerateConfigType: TypeAlias = (
    FGenerateConfig | FlowGenerateConfig | FlowGenerateConfigDict
)
ModelType: TypeAlias = FModel | FlowModel | FlowModelDict
SolverType: TypeAlias = FSolver | FlowSolver | FlowSolverDict
TaskType: TypeAlias = FTask | FlowTask | FlowTaskDict


def to_dict(input: Any) -> dict[str, Any]:
    if isinstance(input, Mapping):
        return dict(input)
    return to_jsonable_python(input, exclude_none=True)


def _merge_dicts(
    base_dict: dict[str, Any],
    add_dict: dict[str, Any],
) -> dict[str, Any]:
    filtered_add_dict = {k: v for k, v in add_dict.items() if v is not None}
    return base_dict | filtered_add_dict


def _merge(
    base: Any,
    add: Any,
) -> dict[str, Any]:
    return _merge_dicts(to_dict(base), to_dict(add))


# Note that current recursive merges do not go deeper than one level
_RECURSIVE_KEYS = {"config", "flow_metadata"}


def merge_recursive(
    base: Any,
    add: Any,
) -> dict[str, Any]:
    base_dict = to_dict(base)
    add_dict = to_dict(add)
    result = _merge_dicts(base_dict, add_dict)
    for key in _RECURSIVE_KEYS:
        if (add_value := add_dict.get(key)) and (base_value := base_dict.get(key)):
            result[key] = _merge(base_value, add_value)
    return result


def agent_merge(
    base: AgentType,
    add: AgentType,
) -> FAgent:
    """Merge two agent configs.

    Args:
        base: The base agent config.
        add: The agent config to merge into the base. Values in this config
            will override those in the base.
    """
    return FAgent.model_validate(merge_recursive(base, add))


def config_merge(
    base: GenerateConfigType,
    add: GenerateConfigType,
) -> FGenerateConfig:
    """Merge two generate configs.

    Args:
        base: The base generate config.
        add: The generate config to merge into the base. Values in this config
            will override those in the base.
    """
    return FGenerateConfig.model_validate(_merge(base, add))


def model_merge(
    base: ModelType,
    add: ModelType,
) -> FModel:
    """Merge two model configs.

    Args:
        base: The base model config.
        add: The model config to merge into the base. Values in this config
            will override those in the base.
    """
    return FModel.model_validate(merge_recursive(base, add))


def solver_merge(
    base: SolverType,
    add: SolverType,
) -> FSolver:
    """Merge two solver configs.

    Args:
        base: The base solver config.
        add: The solver config to merge into the base. Values in this config
            will override those in the base.
    """
    return FSolver.model_validate(merge_recursive(base, add))


def task_merge(
    base: TaskType,
    add: TaskType,
) -> FTask:
    """Merge two task configs.

    Args:
        base: The base task config.
        add: The task config to merge into the base. Values in this config
            will override those in the base.
    """
    return FTask.model_validate(merge_recursive(base, add))
