from inspect_flow import FlowOptions, FlowSpec, tasks_matrix

FlowSpec(
    log_dir="s3://inspect-flow-test/flow_logs/test2",
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=["local_eval/noop", "local_eval/noop2"],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
