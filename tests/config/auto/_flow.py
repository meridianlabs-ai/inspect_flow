from inspect_flow import FlowDefaults, FlowGenerateConfig, FlowJob, FlowModel

FlowJob(
    includes=["_other_flow.py"],
    defaults=FlowDefaults(
        model_prefix={
            "openai": FlowModel(
                base_url="https://api.openai.com/v1/",
                config=FlowGenerateConfig(max_connections=5),
            ),
        }
    ),
)
