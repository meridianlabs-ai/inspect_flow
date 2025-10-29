from itertools import product
from typing import Any, Mapping, TypeVar

from pydantic import BaseModel

from inspect_flow._types.dicts import (
    FlowAgentDict,
    FlowConfigDict,
    FlowModelDict,
    FlowSolverDict,
    FlowTaskDict,
)
from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowConfig,
    FlowModel,
    FlowSolver,
    FlowTask,
)
from inspect_flow._types.matrix_dicts import FlowModelMatrixDict, FlowTaskMatrixDict


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


def _generate(
    base: Mapping[str, Any] | None,
    matrix: Mapping[str, Any],
    pydantic_type: type[_T],
) -> list[_T]:
    if base is None:
        base = {}
    for key in matrix.keys():
        if key in base:
            raise ValueError(f"{key} provided in both base and matrix")
    matrix_keys = matrix.keys()
    result = []
    for matrix_values in product(matrix.values()):
        item_dict = dict(base) | dict(zip(matrix_keys, matrix_values, strict=True))
        result.append(pydantic_type.model_validate(item_dict))
    return result


def models(
    base: FlowModelDict | None = None, *, matrix: FlowModelMatrixDict
) -> list[FlowModel]:
    return _generate(base, matrix, FlowModel)


def tasks(
    base: FlowTaskDict | None = None, *, matrix: FlowTaskMatrixDict
) -> list[FlowTask]:
    return _generate(base, matrix, FlowTask)
