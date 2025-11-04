from inspect_flow._types.flow_types import FConfig
from inspect_flow.types import FlowConfig
from pydantic_core import to_jsonable_python


def fc(config: FlowConfig) -> FConfig:
    return FConfig.model_validate(to_jsonable_python(config))
