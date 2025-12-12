from inspect_flow import FlowOptions, FlowSpec, FlowTask

my_config = FlowSpec(
    log_dir="logs/test",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="openai/gpt-4o-mini",
        ),
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="anthropic/claude-3-5-sonnet",
        ),
    ],
)
