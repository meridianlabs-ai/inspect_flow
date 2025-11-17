from inspect_flow import FlowJob, FlowOptions, FlowTask

my_config = FlowJob(
    flow_dir="logs/model_and_task",
    options=FlowOptions(limit=1),
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
