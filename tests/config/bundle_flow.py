from inspect_flow import FlowJob, FlowOptions, FlowTask

my_config = FlowJob(
    log_dir="logs/bundle_flow",
    options=FlowOptions(limit=1, bundle_dir="{log_dir}/bundle"),
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="openai/gpt-4o-mini",
        )
    ],
)
