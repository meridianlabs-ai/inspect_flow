from itertools import product
from typing import Any, Mapping, Sequence, TypeAlias, TypeVar

from pydantic_core import to_jsonable_python
from typing_extensions import Unpack

from inspect_flow._types.flow_types import (
    FAgent,
    FConfig,
    FGenerateConfig,
    FModel,
    FSolver,
    FTask,
)
from inspect_flow._types.generated import (
    FlowAgent,
    FlowAgentDict,
    FlowAgentMatrixDict,
    FlowConfig,
    FlowConfigDict,
    FlowGenerateConfig,
    FlowGenerateConfigDict,
    FlowGenerateConfigMatrixDict,
    FlowModel,
    FlowModelDict,
    FlowModelMatrixDict,
    FlowSolver,
    FlowSolverDict,
    FlowSolverMatrixDict,
    FlowTask,
    FlowTaskDict,
    FlowTaskMatrixDict,
)
from inspect_flow._types.merge import merge_recursive, to_dict


def flow_agent(config: FlowAgentDict | FlowAgent) -> FAgent:
    """Create an FAgent.

    Args:
        config: The FlowAgent or FlowAgentDict to convert.
    """
    return FAgent.model_validate(to_jsonable_python(config))


def flow_config(config: FlowConfigDict | FlowConfig) -> FConfig:
    """Create an FConfig.

    Args:
        config: The FlowConfig or FlowConfigDict to convert.
    """
    return FConfig.model_validate(to_jsonable_python(config))


def flow_model(config: FlowModelDict | FlowModel) -> FModel:
    """Create an FModel.

    Args:
        config: The FlowModel or FlowModelDict to convert.
    """
    return FModel.model_validate(to_jsonable_python(config))


def flow_solver(config: FlowSolverDict | FlowSolver) -> FSolver:
    """Create an FSolver.

    Args:
        config: The FlowSolver or FlowSolverDict to convert.
    """
    return FSolver.model_validate(to_jsonable_python(config))


def flow_task(config: FlowTaskDict | FlowTask) -> FTask:
    """Create an FTask.

    Args:
        config: The FlowTask or FlowTaskDict to convert.
    """
    return FTask.model_validate(to_jsonable_python(config))


BaseType = TypeVar("BaseType", FAgent, FModel, FSolver, FTask, FGenerateConfig)

AgentType: TypeAlias = FAgent | FlowAgent | FlowAgentDict
GenerateConfigType: TypeAlias = (
    FGenerateConfig | FlowGenerateConfig | FlowGenerateConfigDict
)
ModelType: TypeAlias = FModel | FlowModel | FlowModelDict
SolverType: TypeAlias = FSolver | FlowSolver | FlowSolverDict
TaskType: TypeAlias = FTask | FlowTask | FlowTaskDict

AgentInput: TypeAlias = str | AgentType
GenerateConfigInput: TypeAlias = GenerateConfigType
ModelInput: TypeAlias = str | ModelType
SolverInput: TypeAlias = str | SolverType
TaskInput: TypeAlias = str | TaskType

BaseInputType: TypeAlias = (
    str
    | FAgent
    | FlowAgent
    | FGenerateConfig
    | FlowGenerateConfig
    | FModel
    | FlowModel
    | FSolver
    | FlowSolver
    | FTask
    | FlowTask
    | Mapping[str, Any]
)

BaseInput: TypeAlias = BaseInputType | Sequence[BaseInputType]

MatrixDict = TypeVar(
    "MatrixDict",
    FlowAgentMatrixDict,
    FlowGenerateConfigMatrixDict,
    FlowModelMatrixDict,
    FlowSolverMatrixDict,
    FlowTaskMatrixDict,
)


def _with_base(
    base: BaseInputType,
    values: Mapping[str, Any],
    pydantic_type: type[BaseType],
) -> BaseType:
    base_dict: dict[str, Any] = {}
    if isinstance(base, str):
        base_dict = {"name": base}
    else:
        base_dict = to_dict(base)

    for key in values.keys():
        if key != "config" and key in base_dict:
            raise ValueError(f"{key} provided in both base and values")

    return pydantic_type.model_validate(merge_recursive(base_dict, values))


def _with(
    base: BaseInput,
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
    base: BaseInputType,
    matrix: Mapping[str, Any],
    pydantic_type: type[BaseType],
) -> list[BaseType]:
    base_dict: dict[str, Any] = {}
    if isinstance(base, str):
        base_dict = {"name": base}
    else:
        base_dict = to_dict(base)

    for key in matrix.keys():
        if key != "config" and key in base_dict and base_dict[key] is not None:
            raise ValueError(f"{key} provided in both base and matrix")

    matrix = to_jsonable_python(matrix, exclude_none=True)
    matrix_keys = matrix.keys()
    result = []
    for matrix_values in product(*matrix.values()):
        add_dict = dict(zip(matrix_keys, matrix_values, strict=True))
        result.append(
            pydantic_type.model_validate(merge_recursive(base_dict, add_dict))
        )
    return result


def _matrix(
    base: BaseInput,
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
) -> list[FAgent]:
    """Set fields on a list of agents.

    Args:
        agent: The agent or list of agents to set fields on.
        **kwargs: The fields to set on each agent.
    """
    return _with(agent, kwargs, FAgent)


def configs_with(
    *,
    config: GenerateConfigInput | Sequence[GenerateConfigInput],
    **kwargs: Unpack[FlowGenerateConfigDict],
) -> list[FGenerateConfig]:
    """Set fields on a list of generate configs.

    Args:
        config: The config or list of configs to set fields on.
        **kwargs: The fields to set on each config.
    """
    return _with(config, kwargs, FGenerateConfig)


def models_with(
    *,
    model: ModelInput | Sequence[ModelInput],
    **kwargs: Unpack[FlowModelDict],
) -> list[FModel]:
    """Set fields on a list of models.

    Args:
        model: The model or list of models to set fields on.
        **kwargs: The fields to set on each model.
    """
    return _with(model, kwargs, FModel)


def solvers_with(
    *,
    solver: SolverInput | Sequence[SolverInput],
    **kwargs: Unpack[FlowSolverDict],
) -> list[FSolver]:
    """Set fields on a list of solvers.

    Args:
        solver: The solver or list of solvers to set fields on.
        **kwargs: The fields to set on each solver.
    """
    return _with(solver, kwargs, FSolver)


def tasks_with(
    *,
    task: TaskInput | Sequence[TaskInput],
    **kwargs: Unpack[FlowTaskDict],
) -> list[FTask]:
    """Set fields on a list of tasks.

    Args:
        task: The task or list of tasks to set fields on.
        **kwargs: The fields to set on each task.
    """
    return _with(task, kwargs, FTask)


def agents_matrix(
    *,
    agent: AgentInput | Sequence[AgentInput],
    **kwargs: Unpack[FlowAgentMatrixDict],
) -> list[FAgent]:
    """Create a list of agents from the product of lists of field values.

    Args:
        agent: The agent or list of agents to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(agent, kwargs, FAgent)


def configs_matrix(
    *,
    config: GenerateConfigInput | Sequence[GenerateConfigInput] | None = None,
    **kwargs: Unpack[FlowGenerateConfigMatrixDict],
) -> list[FGenerateConfig]:
    """Create a list of generate configs from the product of lists of field values.

    Args:
        config: The config or list of configs to matrix.
        **kwargs: The lists of field values to matrix.
    """
    config = config or FlowGenerateConfig()
    return _matrix(config, kwargs, FGenerateConfig)


def models_matrix(
    *,
    model: ModelInput | Sequence[ModelInput],
    **kwargs: Unpack[FlowModelMatrixDict],
) -> list[FModel]:
    """Create a list of models from the product of lists of field values.

    Args:
        model: The model or list of models to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(model, kwargs, FModel)


def solvers_matrix(
    *,
    solver: SolverInput | Sequence[SolverInput],
    **kwargs: Unpack[FlowSolverMatrixDict],
) -> list[FSolver]:
    """Create a list of solvers from the product of lists of field values.

    Args:
        solver: The solver or list of solvers to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(solver, kwargs, FSolver)


def tasks_matrix(
    *,
    task: TaskInput | Sequence[TaskInput],
    **kwargs: Unpack[FlowTaskMatrixDict],
) -> list[FTask]:
    """Create a list of tasks from the product of lists of field values.

    Args:
        task: The task or list of tasks to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(task, kwargs, FTask)
