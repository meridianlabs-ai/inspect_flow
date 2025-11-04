from itertools import product
from typing import Any, Mapping, Sequence, TypeAlias, TypeVar

from inspect_ai.model import GenerateConfig
from pydantic import BaseModel

from inspect_flow._types.dicts import (
    FlowAgentDict,
    FlowAgentMatrixDict,
    FlowConfigDict,
    FlowModelDict,
    FlowModelMatrixDict,
    FlowSolverDict,
    FlowSolverMatrixDict,
    FlowTaskDict,
    FlowTaskMatrixDict,
    GenerateConfigDict,
    GenerateConfigMatrixDict,
)
from inspect_flow._types.flow_types import (
    FAgent,
    FConfig,
    FModel,
    FSolver,
    FTask,
)


def flow_config(config: FlowConfigDict) -> FConfig:
    return FConfig.model_validate(config)


def flow_task(config: FlowTaskDict) -> FTask:
    return FTask.model_validate(config)


def flow_model(config: FlowModelDict) -> FModel:
    return FModel.model_validate(config)


def flow_solver(config: FlowSolverDict) -> FSolver:
    return FSolver.model_validate(config)


def flow_agent(config: FlowAgentDict) -> FAgent:
    return FAgent.model_validate(config)


BaseType = TypeVar("BaseType", FAgent, FModel, FSolver, FTask, GenerateConfig)

AgentInput: TypeAlias = str | FAgent | FlowAgentDict
ConfigInput: TypeAlias = GenerateConfig | GenerateConfigDict
ModelInput: TypeAlias = str | FModel | FlowModelDict
SolverInput: TypeAlias = str | FSolver | FlowSolverDict
TaskInput: TypeAlias = str | FTask | FlowTaskDict

BaseInput: TypeAlias = str | BaseModel | Mapping[str, Any]

MatrixDict = TypeVar(
    "MatrixDict",
    FlowAgentMatrixDict,
    GenerateConfigMatrixDict,
    FlowModelMatrixDict,
    FlowSolverMatrixDict,
    FlowTaskMatrixDict,
)


def _with_base(
    base: BaseInput,
    values: Mapping[str, Any],
    pydantic_type: type[BaseType],
) -> BaseType:
    if isinstance(base, str):
        base = {"name": base}
    elif isinstance(base, BaseModel):
        base = base.model_dump(
            exclude_defaults=True, exclude_none=True, exclude_unset=True
        )

    for key in values.keys():
        if key in base:
            raise ValueError(f"{key} provided in both base and values")

    return pydantic_type.model_validate(dict(base) | dict(values))


def _with(
    base: BaseInput | Sequence[BaseInput],
    values: Mapping[str, Any],
    pydantic_type: type[BaseType],
) -> list[BaseType]:
    matrix_dict = dict(values)
    if isinstance(base, Sequence) and not isinstance(base, str):
        return [
            _with_base(
                b,
                matrix_dict,
                pydantic_type,
            )
            for b in base
        ]
    return [_with_base(base, values, pydantic_type)]


def _matrix_with_base(
    base: BaseInput,
    matrix: Mapping[str, Any],
    pydantic_type: type[BaseType],
) -> list[BaseType]:
    if isinstance(base, str):
        base = {"name": base}
    elif isinstance(base, BaseModel):
        base = base.model_dump(
            exclude_defaults=True, exclude_none=True, exclude_unset=True
        )

    for key in matrix.keys():
        if key in base:
            raise ValueError(f"{key} provided in both base and matrix")

    matrix_keys = matrix.keys()
    result = []
    for matrix_values in product(*matrix.values()):
        item_dict = dict(base) | dict(zip(matrix_keys, matrix_values, strict=True))
        result.append(pydantic_type.model_validate(item_dict))
    return result


def _matrix(
    base: BaseInput | Sequence[BaseInput],
    matrix: MatrixDict,
    pydantic_type: type[BaseType],
) -> list[BaseType]:
    matrix_dict = dict(matrix)
    if isinstance(base, Sequence) and not isinstance(base, str):
        return [
            item
            for b in base
            for item in _matrix_with_base(
                b,
                matrix_dict,
                pydantic_type,
            )
        ]
    return _matrix_with_base(base, matrix_dict, pydantic_type)


def agents_with(
    agent: AgentInput | Sequence[AgentInput],
    values: FlowAgentDict,
) -> list[FAgent]:
    return _with(agent, values, FAgent)


def configs_with(
    config: ConfigInput | Sequence[ConfigInput],
    values: GenerateConfigDict,
) -> list[GenerateConfig]:
    return _with(config, values, GenerateConfig)


def models_with(
    model: ModelInput | Sequence[ModelInput],
    values: FlowModelDict,
) -> list[FModel]:
    return _with(model, values, FModel)


def solvers_with(
    solver: SolverInput | Sequence[SolverInput],
    values: FlowSolverDict,
) -> list[FSolver]:
    return _with(solver, values, FSolver)


def tasks_with(
    task: TaskInput | Sequence[TaskInput],
    values: FlowTaskDict,
) -> list[FTask]:
    return _with(task, values, FTask)


def agents_matrix(
    agent: AgentInput | Sequence[AgentInput],
    matrix: FlowAgentMatrixDict,
) -> list[FAgent]:
    return _matrix(agent, matrix, FAgent)


def configs_matrix(
    config: ConfigInput | Sequence[ConfigInput],
    matrix: GenerateConfigMatrixDict,
) -> list[GenerateConfig]:
    return _matrix(config, matrix, GenerateConfig)


def models_matrix(
    model: ModelInput | Sequence[ModelInput],
    matrix: FlowModelMatrixDict,
) -> list[FModel]:
    return _matrix(model, matrix, FModel)


def solvers_matrix(
    solver: SolverInput | Sequence[SolverInput],
    matrix: FlowSolverMatrixDict,
) -> list[FSolver]:
    return _matrix(solver, matrix, FSolver)


def tasks_matrix(
    task: TaskInput | Sequence[TaskInput],
    matrix: FlowTaskMatrixDict,
) -> list[FTask]:
    return _matrix(task, matrix, FTask)
