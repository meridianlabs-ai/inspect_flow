from inspect_flow import FlowJob, FlowTask

FlowJob(
    log_dir="logs",  # <1>
    dependencies=["inspect-evals"],  # <2>
    tasks=[  # <3>
        FlowTask(
            name="inspect_evals/gpqa_diamond",  # <4>
            model="openai/gpt-5",  # <5>
        ),
    ],
)
