from itertools import product
from typing import Any, Mapping, TypeVar

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


_T = TypeVar("_T", bound=BaseModel)


def _generate_from_base(
    base: Mapping[str, Any] | str | BaseModel,
    matrix: dict[str, Any],
    pydantic_type: type[_T],
) -> list[_T]:
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
    matrix: Mapping[str, Any], pydantic_type: type[_T], base_attr_name: str
) -> list[_T]:
    matrix_dict = dict(matrix)
    base = matrix_dict.pop(base_attr_name, {})
    if isinstance(base, list):
        return [
            item
            for b in base
            for item in _generate_from_base(
                b.model_dump(
                    exclude_defaults=True, exclude_none=True, exclude_unset=True
                ),
                matrix_dict,
                pydantic_type,
            )
        ]
    return _generate_from_base(base, matrix_dict, pydantic_type)


def solvers(
    *,
    matrix: FlowSolverMatrixDict,
) -> list[FlowSolver]:
    return _generate(matrix, FlowSolver, "solver")


def agents(
    *,
    matrix: FlowAgentMatrixDict,
) -> list[FlowAgent]:
    return _generate(matrix, FlowAgent, "agent")


def models(
    *,
    matrix: FlowModelMatrixDict,
) -> list[FlowModel]:
    return _generate(matrix, FlowModel, "model")


def tasks(
    *,
    matrix: FlowTaskMatrixDict,
) -> list[FlowTask]:
    return _generate(matrix, FlowTask, "task")


def configs(
    *,
    matrix: GenerateConfigMatrixDict,
) -> list[GenerateConfig]:
    return _generate(matrix, GenerateConfig, "config")
