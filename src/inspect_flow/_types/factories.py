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
    FlowAgent,
    FlowConfig,
    FlowModel,
    FlowSolver,
    FlowTask,
)


def flow_config(config: FlowConfigDict) -> FlowConfig:
    return FlowConfig.model_validate(config)


def flow_task(config: FlowTaskDict) -> FlowTask:
    return FlowTask.model_validate(config)


def flow_model(config: FlowModelDict) -> FlowModel:
    return FlowModel.model_validate(config)


def flow_solver(config: FlowSolverDict) -> FlowSolver:
    return FlowSolver.model_validate(config)


def flow_agent(config: FlowAgentDict) -> FlowAgent:
    return FlowAgent.model_validate(config)


BaseType = TypeVar(
    "BaseType", FlowAgent, FlowModel, FlowSolver, FlowTask, GenerateConfig
)

AgentInput: TypeAlias = str | FlowAgent | FlowAgentDict
ConfigInput: TypeAlias = GenerateConfig | GenerateConfigDict
ModelInput: TypeAlias = str | FlowModel | FlowModelDict
SolverInput: TypeAlias = str | FlowSolver | FlowSolverDict
TaskInput: TypeAlias = str | FlowTask | FlowTaskDict

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
    if isinstance(base, Sequence):
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
    if isinstance(base, Sequence):
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
    agents: AgentInput | Sequence[AgentInput],
    values: FlowAgentDict,
) -> list[FlowAgent]:
    return _with(agents, values, FlowAgent)


def configs_with(
    configs: ConfigInput | Sequence[ConfigInput],
    values: GenerateConfigDict,
) -> list[GenerateConfig]:
    return _with(configs, values, GenerateConfig)


def models_with(
    models: ModelInput | Sequence[ModelInput],
    values: FlowModelDict,
) -> list[FlowModel]:
    return _with(models, values, FlowModel)


def solvers_with(
    solvers: SolverInput | Sequence[SolverInput],
    values: FlowSolverDict,
) -> list[FlowSolver]:
    return _with(solvers, values, FlowSolver)


def tasks_with(
    tasks: TaskInput | Sequence[TaskInput],
    values: FlowTaskDict,
) -> list[FlowTask]:
    return _with(tasks, values, FlowTask)


def agents_matrix(
    agents: AgentInput | Sequence[AgentInput],
    matrix: FlowAgentMatrixDict,
) -> list[FlowAgent]:
    return _matrix(agents, matrix, FlowAgent)


def configs_matrix(
    configs: ConfigInput | Sequence[ConfigInput],
    matrix: GenerateConfigMatrixDict,
) -> list[GenerateConfig]:
    return _matrix(configs, matrix, GenerateConfig)


def models_matrix(
    models: ModelInput | Sequence[ModelInput],
    matrix: FlowModelMatrixDict,
) -> list[FlowModel]:
    return _matrix(models, matrix, FlowModel)


def solvers_matrix(
    solvers: SolverInput | Sequence[SolverInput],
    matrix: FlowSolverMatrixDict,
) -> list[FlowSolver]:
    return _matrix(solvers, matrix, FlowSolver)


def tasks_matrix(
    tasks: TaskInput | Sequence[TaskInput],
    matrix: FlowTaskMatrixDict,
) -> list[FlowTask]:
    return _matrix(tasks, matrix, FlowTask)
