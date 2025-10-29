from itertools import product

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
from inspect_flow._types.matrix_dicts import FlowTaskMatrixDict


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


def tasks(base: FlowTaskDict, *, matrix: FlowTaskMatrixDict) -> list[FlowTask]:
    for key in matrix.keys():
        if key in base:
            raise ValueError(f"{key} provided in both base and matrix")
    matrix_keys = matrix.keys()
    result = []
    for matrix_values in product(matrix.values()):
        task_dict = base | dict(zip(matrix_keys, matrix_values, strict=True))
        result.append(FlowTask.model_validate(task_dict))
    return result
