from inspect_flow import tasks_with
from inspect_flow.types import _FlowConfig, _FlowOptions

_FlowConfig(
    flow_dir="./logs/local_logs",
    options=_FlowOptions(limit=1),
    dependencies=[
        "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
    ],
    tasks=tasks_with(
        ["inspect_evals/mbpp", "inspect_evals/class_eval"],
        {"model": "openai/gpt-4o-mini"},
    ),
)
