from inspect_flow import tasks_matrix
from inspect_flow.types import _FlowConfig, _FlowOptions

_FlowConfig(
    flow_dir="./logs/local_logs",
    options=_FlowOptions(limit=1),
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=tasks_matrix(
        ["local_eval/noop", "local_eval/noop2"],
        {
            "model": ["mockllm/mock-llm1", "mockllm/mock-llm2"],
        },
    ),
)
