from inspect_flow import FlowConfig, FlowOptions, FlowTask

FlowConfig(
    flow_dir="logs/flow_test",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="local_eval/src/local_eval/noop.py@noop",
            model="mockllm/mock-llm",
        ),
    ],
)
