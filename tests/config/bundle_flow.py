from inspect_flow import FlowOptions, FlowSpec, FlowTask

my_config = FlowSpec(
    log_dir="logs/bundle_flow",
    options=FlowOptions(limit=1, bundle_dir="logs/bundle"),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o-mini",
        )
    ],
)
