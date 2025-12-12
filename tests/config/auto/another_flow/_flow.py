from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowModel, FlowSpec

FlowSpec(
    defaults=FlowDefaults(
        model_prefix={
            "anthropic": FlowModel(
                base_url="https://api.anthropic.com/v1/",
                config=GenerateConfig(max_connections=10),
            ),
        }
    ),
)
