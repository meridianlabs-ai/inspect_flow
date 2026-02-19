from inspect_flow import FlowOptions, FlowSpec, FlowTask

my_config = FlowSpec(
    log_dir="logs/mock_flow",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="local_eval/noop",
            model="mockllm/mock-llm",
        )
    ],
)
