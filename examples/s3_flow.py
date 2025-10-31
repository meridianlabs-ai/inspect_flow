from inspect_flow._types.factories import tasks
from inspect_flow._types.flow_types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="s3://inspect-flow-test/flow_logs/test2",
    options=FlowOptions(limit=1),
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=tasks(
        matrix={
            "name": ["local_eval/noop", "local_eval/noop2"],
            "model": ["mockllm/mock-llm1", "mockllm/mock-llm2"],
        },
    ),
)
