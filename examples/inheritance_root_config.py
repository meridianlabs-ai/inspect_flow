from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowSpec

FlowSpec(
    defaults=FlowDefaults(
        config=GenerateConfig(
            max_connections=10,
            temperature=0.0,
        ),
    ),
)
