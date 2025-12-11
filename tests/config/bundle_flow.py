from inspect_flow import FlowOptions, FlowSpec, FlowTask

my_config = FlowSpec(
    log_dir="logs/bundle_flow",
    options=FlowOptions(limit=1, bundle_dir="{log_dir}/bundle"),
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="openai/gpt-4o-mini",
        )
    ],
)
