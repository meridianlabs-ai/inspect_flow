from inspect_flow import FlowJob, FlowModel, FlowOptions, FlowTask, tasks_matrix

FlowJob(
    log_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=[
            FlowTask(args={"fail": True}),
            "local_eval/noop",
            "local_eval/noop2",
        ],
        model=[
            "mockllm/mock-llm1",
            "mockllm/mock-llm2",
            FlowModel(name="mockllm/mock-llm3"),
            FlowModel(base_url="http://localhost:8000"),  # Missing 'name' field
        ],
    ),
)
