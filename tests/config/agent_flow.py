from inspect_flow import tasks_with
from inspect_flow.types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=[
        "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
    ],
    tasks=tasks_with(
        task=["inspect_evals/mbpp", "inspect_evals/class_eval"],
        model="openai/gpt-4o-mini",
    ),
)
