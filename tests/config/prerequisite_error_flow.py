from inspect_flow import FlowConfig, FlowOptions, FlowTask

FlowConfig(
    flow_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=[
        "./tests/config/local_eval",
    ],
    tasks=[
        FlowTask(name="local_eval/noop", model="mockllm/mock-llm1"),
        FlowTask(name="local_eval/noop", model="mockllm/mock-llm1"),
    ],
)
