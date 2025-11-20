from inspect_flow import FlowJob, FlowOptions, FlowTask

my_config = FlowJob(
    log_dir="logs/bundle_flow",
    options=FlowOptions(limit=1, bundle_dir="{log_dir}/bundle"),
    dependencies=[
        "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
    ],
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="openai/gpt-4o-mini",
        )
    ],
)
