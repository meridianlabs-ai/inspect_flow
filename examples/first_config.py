from inspect_flow import FlowJob, FlowTask

FlowJob(
    tasks=[  # <1>
        FlowTask(
            name="inspect_evals/gpqa_diamond",  # <2>
            model="openai/gpt-5",  # <3>
        ),
    ],
)
