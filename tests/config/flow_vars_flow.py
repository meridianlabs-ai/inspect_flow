from inspect_flow import FlowJob, FlowOptions, FlowTask

model_variable = globals().get("__flow_vars__", {}).get("model", None)
assert model_variable == locals().get("__flow_vars__", {}).get("model", None)

my_config = FlowJob(
    log_dir="logs/model_and_task",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model=model_variable or "openai/gpt-4o-mini",
        )
    ],
)
