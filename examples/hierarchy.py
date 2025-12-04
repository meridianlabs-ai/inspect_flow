from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowJob, FlowModel, FlowTask

FlowJob(
    defaults=FlowDefaults(
        config=GenerateConfig(
            temperature=0.0,  # <1>
            max_tokens=100,  # <1>
        ),
        model_prefix={
            "openai/": FlowModel(
                config=GenerateConfig(temperature=0.5)  # <2>
            )
        },
    ),
    tasks=[
        FlowTask(
            name="task",
            config=GenerateConfig(temperature=0.7),  # <3>
            model=FlowModel(
                name="openai/gpt-4o",
                config=GenerateConfig(temperature=1.0),  # <4>
            ),
        )
    ],
)
