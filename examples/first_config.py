from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",  # <1>
    tasks=[  # <2>
        FlowTask(
            name="inspect_evals/gpqa_diamond",  # <3>
            model="openai/gpt-5",  # <4>
        ),
    ],
)
