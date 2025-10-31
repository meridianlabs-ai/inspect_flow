from inspect_flow._types.factories import tasks
from inspect_flow._types.flow_types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="./logs/local_logs",
    options=FlowOptions(limit=1),
    dependencies=[
        "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
    ],
    tasks=tasks(
        matrix={
            "task": {"model": "openai/gpt-4o-mini"},
            "name": ["inspect_evals/mbpp", "inspect_evals/class_eval"],
        },
    ),
)
