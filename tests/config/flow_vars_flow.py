from inspect_flow.types import FlowConfig, FlowTask

model_variable = globals().get("__flow_vars__", {}).get("model", None)
assert model_variable == locals().get("__flow_vars__", {}).get("model", None)

my_config = FlowConfig(
    flow_dir="logs/model_and_task",
    options={"limit": 1},
    dependencies=[
        "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
    ],
    tasks=[
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model=model_variable or "openai/gpt-4o-mini",
        )
    ],
)
