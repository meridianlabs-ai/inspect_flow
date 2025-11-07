from inspect_flow import tasks_matrix
from inspect_flow.types import FlowConfig, FlowOptions

FlowConfig(
    flow_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from a package
            "local_eval/src/local_eval/noop.py@noop",  # task from a file relative to the config
            "examples/local_eval/src/local_eval/noop.py@noop",  # task from a file relative to cwd
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
