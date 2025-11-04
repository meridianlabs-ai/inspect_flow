from inspect_flow._types.factories import flow_task
from inspect_flow.types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="./logs/local_logs",
    options=FlowOptions(limit=1),
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=[
        flow_task({"name": "local_eval/noop", "model": "mockllm/mock-llm1"}),
        flow_task({"name": "local_eval/noop", "model": "mockllm/mock-llm1"}),
    ],
)
