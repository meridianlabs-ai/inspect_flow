from inspect_flow import FlowJob, FlowOptions, FlowTask

my_config = FlowJob(
    log_dir="logs/model_and_task",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="openai/gpt-4o-mini",
        )
    ],
)
