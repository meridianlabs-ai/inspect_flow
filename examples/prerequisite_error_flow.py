from inspect_flow._types.factories import tasks
from inspect_flow._types.flow_types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="./logs/local_logs",
    options=FlowOptions(limit=1),
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=tasks(
        matrix={
            "task": {"name": "local_eval/noop", "model": "mockllm/mock-llm1"},
            "message_limit": [4, 5],
        },
    ),
)
