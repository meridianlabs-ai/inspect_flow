from inspect_flow import FlowConfig, FlowOptions, FlowTask, tasks_matrix

FlowConfig(
    flow_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=[
        "./tests/config/local_eval",
    ],
    tasks=tasks_matrix(
        task=[
            FlowTask(args={"fail": True}),
            "local_eval/noop",
            "local_eval/noop2",
        ],
        model=[
            "mockllm/mock-llm1",
            "mockllm/mock-llm2",
            {"name": "mockllm/mock-llm3"},
            {"base_url": "http://localhost:8000"},  # Missing 'name' field
        ],
    ),
)
