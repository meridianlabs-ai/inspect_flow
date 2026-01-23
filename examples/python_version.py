from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    execution_type="venv",  # <1>
    python_version="3.11",
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-5",
        ),
    ],
)
