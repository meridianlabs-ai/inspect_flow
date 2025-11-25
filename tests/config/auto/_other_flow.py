from inspect_flow import FlowDefaults, FlowJob, FlowModel, GenerateConfig

FlowJob(
    defaults=FlowDefaults(
        model_prefix={
            "antropic": FlowModel(
                base_url="https://api.anthropic.com/v1/",
                config=GenerateConfig(max_connections=2),
            ),
        }
    )
)
