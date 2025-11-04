from itertools import product
from typing import Any, Mapping, Sequence, TypeAlias, TypeVar, Unpack

from inspect_ai.model import GenerateConfig
from pydantic import BaseModel

from inspect_flow._types.dicts import (
    FlowAgent,
    FlowAgentDict,
    FlowAgentMatrixDict,
    FlowConfig,
    FlowConfigDict,
    FlowModel,
    FlowModelDict,
    FlowModelMatrixDict,
    FlowSolver,
    FlowSolverDict,
    FlowSolverMatrixDict,
    FlowTask,
    FlowTaskDict,
    FlowTaskMatrixDict,
    GenerateConfigDict,
    GenerateConfigMatrixDict,
)
from inspect_flow._types.flow_types import (
    FAgent,
    FModel,
    FSolver,
    FTask,
)


def flow_config(config: FlowConfigDict | FlowConfig) -> FlowConfig:
    return FlowConfig.model_validate(config)


def flow_task(config: FlowTaskDict | FlowTask) -> FlowTask:
    return FlowTask.model_validate(config)


def flow_model(config: FlowModelDict | FlowModel) -> FlowModel:
    return FlowModel.model_validate(config)


def flow_solver(config: FlowSolverDict | FlowSolver) -> FlowSolver:
    return FlowSolver.model_validate(config)


def flow_agent(config: FlowAgentDict | FlowAgent) -> FlowAgent:
    return FlowAgent.model_validate(config)


BaseType = TypeVar(
    "BaseType", FlowAgent, FlowModel, FlowSolver, FlowTask, GenerateConfig
)

AgentInput: TypeAlias = str | FAgent | FlowAgent | FlowAgentDict
ConfigInput: TypeAlias = GenerateConfig | GenerateConfigDict
ModelInput: TypeAlias = str | FModel | FlowModel | FlowModelDict
SolverInput: TypeAlias = str | FSolver | FlowSolver | FlowSolverDict
TaskInput: TypeAlias = str | FTask | FlowTask | FlowTaskDict

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
    *,
    agent: AgentInput | Sequence[AgentInput],
    **kwargs: Unpack[FlowAgentDict],
) -> list[FlowAgent]:
    return _with(agent, kwargs, FlowAgent)


def configs_with(
    *,
    config: ConfigInput | Sequence[ConfigInput],
    **kwargs: Unpack[GenerateConfigDict],
) -> list[GenerateConfig]:
    return _with(config, kwargs, GenerateConfig)


def models_with(
    *,
    model: ModelInput | Sequence[ModelInput],
    **kwargs: Unpack[FlowModelDict],
) -> list[FlowModel]:
    return _with(model, kwargs, FlowModel)


def solvers_with(
    *,
    solver: SolverInput | Sequence[SolverInput],
    **kwargs: Unpack[FlowSolverDict],
) -> list[FlowSolver]:
    return _with(solver, kwargs, FlowSolver)


def tasks_with(
    *,
    task: TaskInput | Sequence[TaskInput],
    **kwargs: Unpack[FlowTaskDict],
) -> list[FlowTask]:
    return _with(task, kwargs, FlowTask)


def agents_matrix(
    *,
    agent: AgentInput | Sequence[AgentInput],
    **kwargs: Unpack[FlowAgentMatrixDict],
) -> list[FlowAgent]:
    return _matrix(agent, kwargs, FlowAgent)


def configs_matrix(
    *,
    config: ConfigInput | Sequence[ConfigInput],
    **kwargs: Unpack[GenerateConfigMatrixDict],
) -> list[GenerateConfig]:
    return _matrix(config, kwargs, GenerateConfig)


def models_matrix(
    *,
    model: ModelInput | Sequence[ModelInput],
    **kwargs: Unpack[FlowModelMatrixDict],
) -> list[FlowModel]:
    return _matrix(model, kwargs, FlowModel)


def solvers_matrix(
    *,
    solver: SolverInput | Sequence[SolverInput],
    **kwargs: Unpack[FlowSolverMatrixDict],
) -> list[FlowSolver]:
    return _matrix(solver, kwargs, FlowSolver)


def tasks_matrix(
    *,
    task: TaskInput | Sequence[TaskInput],
    **kwargs: Unpack[FlowTaskMatrixDict],
) -> list[FlowTask]:
    return _matrix(task, kwargs, FlowTask)
