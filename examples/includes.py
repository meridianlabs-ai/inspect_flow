from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    includes=[
        "defaults.py",
        "../shared.py",
        "/absolute/path.py",
    ],
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
        ),
    ],
)
