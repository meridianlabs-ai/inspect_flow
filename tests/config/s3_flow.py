from inspect_flow import FlowJob, FlowOptions, tasks_matrix

FlowJob(
    log_dir="s3://inspect-flow-test/flow_logs/test2",
    options=FlowOptions(limit=1),
    dependencies=[
        "./tests/config/local_eval",
    ],
    tasks=tasks_matrix(
        task=["local_eval/noop", "local_eval/noop2"],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
