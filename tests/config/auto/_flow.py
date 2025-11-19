from inspect_flow import FlowDefaults, FlowGenerateConfig, FlowJob, FlowModel

FlowJob(
    defaults=FlowDefaults(
        model_prefix={
            "antropic": FlowModel(
                base_url="https://api.anthropic.com/v1/",
                config=FlowGenerateConfig(max_connections=2),
            ),
            "openai": FlowModel(
                base_url="https://api.openai.com/v1/",
                config=FlowGenerateConfig(max_connections=5),
            ),
        }
    )
)
