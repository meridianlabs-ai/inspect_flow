from inspect_flow import FlowDefaults, FlowGenerateConfig, FlowJob, FlowModel, FlowTask

FlowJob(
    defaults=FlowDefaults(
        config=FlowGenerateConfig(
            temperature=0.0,  # <1>
            max_tokens=100,  # <1>
        ),
        model_prefix={
            "openai/": FlowModel(
                config=FlowGenerateConfig(temperature=0.5)  # <2>
            )
        },
    ),
    tasks=[
        FlowTask(
            name="task",
            config=FlowGenerateConfig(temperature=0.7),  # <3>
            model=FlowModel(
                name="openai/gpt-4o",
                config=FlowGenerateConfig(temperature=1.0),  # <4>
            ),
        )
    ],
)
