from inspect_flow import flow_config, tasks_matrix
from inspect_flow._cli.main import flow
from inspect_flow._types.flow_types import _FlowConfig, _FlowOptions, _FlowTask

flow_config(
    {
        "flow_dir": "./logs/local_logs",
        "options": {"limit": 1},
        "dependencies": [
            "./examples/local_eval",
        ],
        "tasks": []
        
        tasks_matrix(
            ["local_eval/noop", "local_eval/noop2"],
            {
                "model": [
                    "mockllm/mock-llm1",
                    "mockllm/mock-llm2",
                    {"name": "mockllm/mock-llm3", "version": "v1.0"},  # pyright: ignore[reportArgumentType]
                ],
            },
        ),
    }
)

FlowConfigStrict

_FlowConfig(
    flow_dir="./logs/local_logs",
    options={"limit": 1},
    dependencies=[
        "./examples/local_eval",
    ],
    tasks=[_FlowTask(name="local_eval/noop")],
)