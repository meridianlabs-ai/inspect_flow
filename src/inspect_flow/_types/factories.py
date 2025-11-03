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


def _generate_from_base(
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


def _generate(
    base: BaseInput | Sequence[BaseInput],
    matrix: MatrixDict,
    pydantic_type: type[BaseType],
) -> Sequence[BaseType]:
    matrix_dict = dict(matrix)
    if isinstance(base, Sequence):
        return [
            item
            for b in base
            for item in _generate_from_base(
                b,
                matrix_dict,
                pydantic_type,
            )
        ]
    return _generate_from_base(base, matrix_dict, pydantic_type)


def agents_matrix(
    agents: AgentInput | Sequence[AgentInput],
    matrix: FlowAgentMatrixDict,
) -> Sequence[FlowAgent]:
    return _generate(agents, matrix, FlowAgent)


def configs_matrix(
    configs: ConfigInput | Sequence[ConfigInput],
    matrix: GenerateConfigMatrixDict,
) -> Sequence[GenerateConfig]:
    return _generate(configs, matrix, GenerateConfig)


def models_matrix(
    models: ModelInput | Sequence[ModelInput],
    matrix: FlowModelMatrixDict,
) -> Sequence[FlowModel]:
    return _generate(models, matrix, FlowModel)


def solvers_matrix(
    solvers: SolverInput | Sequence[SolverInput],
    matrix: FlowSolverMatrixDict,
) -> Sequence[FlowSolver]:
    return _generate(solvers, matrix, FlowSolver)


def tasks_matrix(
    tasks: TaskInput | Sequence[TaskInput],
    matrix: FlowTaskMatrixDict,
) -> Sequence[FlowTask]:
    return _generate(tasks, matrix, FlowTask)
