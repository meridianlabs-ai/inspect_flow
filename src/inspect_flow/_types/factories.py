from itertools import product
from typing import Any, Mapping, Sequence, TypeVar

from typing_extensions import Unpack

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
)
from inspect_flow._types.generated import (
    FlowAgentDict,
    FlowAgentMatrixDict,
    FlowModelDict,
    FlowModelMatrixDict,
    FlowSolverDict,
    FlowSolverMatrixDict,
    FlowTaskDict,
    FlowTaskMatrixDict,
    GenerateConfigDict,
    GenerateConfigMatrixDict,
)
from inspect_flow._types.merge import merge_recursive, to_dict

BaseType = TypeVar(
    "BaseType", FlowAgent, FlowModel, FlowSolver, FlowTask, GenerateConfig
)

MatrixDict = (
    FlowAgentMatrixDict
    | GenerateConfigMatrixDict
    | FlowModelMatrixDict
    | FlowSolverMatrixDict
    | FlowTaskMatrixDict
)


def _with_base(
    base: str | BaseType,
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

    return pydantic_type.model_validate(
        merge_recursive(base_dict, values), extra="forbid"
    )


def _with(
    base: str | BaseType | Sequence[str | BaseType],
    values: Mapping[str, Any],
    pydantic_type: type[BaseType],
) -> list[BaseType]:
    if isinstance(base, Sequence) and not isinstance(base, str):
        return [
            _with_base(
                b,
                values,
                pydantic_type,
            )
            for b in base
        ]
    return [_with_base(base, values, pydantic_type)]


def _matrix_with_base(
    base: str | BaseType,
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

    matrix_keys = matrix.keys()
    result = []
    for matrix_values in product(*matrix.values()):
        add_dict = dict(zip(matrix_keys, matrix_values, strict=True))
        result.append(
            pydantic_type.model_validate(
                merge_recursive(base_dict, add_dict), extra="forbid"
            )
        )
    return result


def _matrix(
    base: str | BaseType | Sequence[str | BaseType],
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
    agent: str | FlowAgent | Sequence[str | FlowAgent],
    **kwargs: Unpack[FlowAgentDict],
) -> list[FlowAgent]:
    """Set fields on a list of agents.

    Args:
        agent: The agent or list of agents to set fields on.
        **kwargs: The fields to set on each agent.
    """
    return _with(agent, kwargs, FlowAgent)


def configs_with(
    *,
    config: GenerateConfig | Sequence[GenerateConfig],
    **kwargs: Unpack[GenerateConfigDict],
) -> list[GenerateConfig]:
    """Set fields on a list of generate configs.

    Args:
        config: The config or list of configs to set fields on.
        **kwargs: The fields to set on each config.
    """
    return _with(config, kwargs, GenerateConfig)


def models_with(
    *,
    model: str | FlowModel | Sequence[str | FlowModel],
    **kwargs: Unpack[FlowModelDict],
) -> list[FlowModel]:
    """Set fields on a list of models.

    Args:
        model: The model or list of models to set fields on.
        **kwargs: The fields to set on each model.
    """
    return _with(model, kwargs, FlowModel)


def solvers_with(
    *,
    solver: str | FlowSolver | Sequence[str | FlowSolver],
    **kwargs: Unpack[FlowSolverDict],
) -> list[FlowSolver]:
    """Set fields on a list of solvers.

    Args:
        solver: The solver or list of solvers to set fields on.
        **kwargs: The fields to set on each solver.
    """
    return _with(solver, kwargs, FlowSolver)


def tasks_with(
    *,
    task: str | FlowTask | Sequence[str | FlowTask],
    **kwargs: Unpack[FlowTaskDict],
) -> list[FlowTask]:
    """Set fields on a list of tasks.

    Args:
        task: The task or list of tasks to set fields on.
        **kwargs: The fields to set on each task.
    """
    return _with(task, kwargs, FlowTask)


def agents_matrix(
    *,
    agent: str | FlowAgent | Sequence[str | FlowAgent],
    **kwargs: Unpack[FlowAgentMatrixDict],
) -> list[FlowAgent]:
    """Create a list of agents from the product of lists of field values.

    Args:
        agent: The agent or list of agents to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(agent, kwargs, FlowAgent)


def configs_matrix(
    *,
    config: GenerateConfig | Sequence[GenerateConfig] | None = None,
    **kwargs: Unpack[GenerateConfigMatrixDict],
) -> list[GenerateConfig]:
    """Create a list of generate configs from the product of lists of field values.

    Args:
        config: The config or list of configs to matrix.
        **kwargs: The lists of field values to matrix.
    """
    config = config or GenerateConfig()
    return _matrix(config, kwargs, GenerateConfig)


def models_matrix(
    *,
    model: str | FlowModel | Sequence[str | FlowModel],
    **kwargs: Unpack[FlowModelMatrixDict],
) -> list[FlowModel]:
    """Create a list of models from the product of lists of field values.

    Args:
        model: The model or list of models to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(model, kwargs, FlowModel)


def solvers_matrix(
    *,
    solver: str | FlowSolver | Sequence[str | FlowSolver],
    **kwargs: Unpack[FlowSolverMatrixDict],
) -> list[FlowSolver]:
    """Create a list of solvers from the product of lists of field values.

    Args:
        solver: The solver or list of solvers to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(solver, kwargs, FlowSolver)


def tasks_matrix(
    *,
    task: str | FlowTask | Sequence[str | FlowTask],
    **kwargs: Unpack[FlowTaskMatrixDict],
) -> list[FlowTask]:
    """Create a list of tasks from the product of lists of field values.

    Args:
        task: The task or list of tasks to matrix.
        **kwargs: The lists of field values to matrix.
    """
    return _matrix(task, kwargs, FlowTask)
