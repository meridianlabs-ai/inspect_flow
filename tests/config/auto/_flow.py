from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowJob, FlowModel

FlowJob(
    includes=["_other_flow.py"],
    defaults=FlowDefaults(
        model_prefix={
            "openai": FlowModel(
                base_url="https://api.openai.com/v1/",
                config=GenerateConfig(max_connections=5),
            ),
        }
    ),
)
