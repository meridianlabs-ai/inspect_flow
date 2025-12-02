from inspect_flow import FlowJob, FlowTask

FlowJob(
    python_version="3.11",
    log_dir="logs",
    tasks=[  # <2>
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-5",
        ),
    ],
)
