from inspect_flow import FlowJob, FlowTask

FlowJob(
    dependencies=["inspect-evals"],  # <1>
    tasks=[  # <2>
        FlowTask(
            name="inspect_evals/gpqa_diamond",  # <3>
            model="openai/gpt-5",  # <4>
        ),
    ],
)
