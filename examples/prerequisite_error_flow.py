from inspect_flow import tasks_matrix
from inspect_flow.types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="./logs/local_logs",
    options=FlowOptions(limit=1),
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=tasks_matrix(
        {"name": "local_eval/noop", "model": "mockllm/mock-llm1"},
        {
            "message_limit": [4, 5],
        },
    ),
)
