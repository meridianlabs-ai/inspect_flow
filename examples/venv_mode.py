from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
    execution_type="venv",  # <1>
    python_version="3.11",  # <2>
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4",
        ),
    ],
)
