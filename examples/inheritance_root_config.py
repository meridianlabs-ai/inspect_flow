from inspect_flow import FlowDefaults, FlowJob, GenerateConfig

FlowJob(
    defaults=FlowDefaults(
        config=GenerateConfig(
            max_connections=10,
            temperature=0.0,
        ),
    ),
)
