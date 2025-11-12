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


def _merge_untyped(
    base: Any,
    add: Any,
) -> dict[str, Any]:
    return _merge_dicts(to_dict(base), to_dict(add))


def merge_with_config(
    base: Any,
    add: Any,
) -> dict[str, Any]:
    base_dict = to_dict(base)
    add_dict = to_dict(add)
    result = _merge_dicts(base_dict, add_dict)
    if (add_config := add_dict.get("config")) and (
        base_config := base_dict.get("config")
    ):
        result["config"] = _merge_untyped(base_config, add_config)
    return result


def agent_merge(
    base: AgentType,
    add: AgentType,
) -> FAgent:
    return FAgent.model_validate(merge_with_config(base, add))


def config_merge(
    base: GenerateConfigType,
    add: GenerateConfigType,
) -> FGenerateConfig:
    return FGenerateConfig.model_validate(_merge_untyped(base, add))


def model_merge(
    base: ModelType,
    add: ModelType,
) -> FModel:
    return FModel.model_validate(merge_with_config(base, add))


def solver_merge(
    base: SolverType,
    add: SolverType,
) -> FSolver:
    return FSolver.model_validate(merge_with_config(base, add))


def task_merge(
    base: TaskType,
    add: TaskType,
) -> FTask:
    return FTask.model_validate(merge_with_config(base, add))
