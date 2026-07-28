from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowSpec

FlowSpec(
    defaults=FlowDefaults(
        config=GenerateConfig(temperature=0.5),
    ),
)
