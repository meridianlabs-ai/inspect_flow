from inspect_flow import FlowOptions, FlowSpec, tasks_with

FlowSpec(
    log_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    tasks=tasks_with(
        task=["inspect_evals/mbpp", "inspect_evals/class_eval"],
        model="openai/gpt-4o-mini",
    ),
)
