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
