from inspect_flow._types.flow_types import FConfig, FTask
from inspect_flow.types import FlowConfig, FlowTask


def fc(config: FlowConfig) -> FConfig:
    return FConfig.model_validate(config.model_dump())


def ft(config: FlowTask) -> FTask:
    return FTask.model_validate(config.model_dump())
