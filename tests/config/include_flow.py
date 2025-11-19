from inspect_flow import FlowInclude, FlowJob, FlowOptions, tasks_matrix

FlowJob(
    includes=[FlowInclude(config_file_path="defaults_flow.py")],
    log_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=[
        "./tests/config/local_eval",
    ],
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from a package
            "local_eval/src/local_eval/noop.py@noop",  # task from a file relative to the config
            "tests/config/local_eval/src/local_eval/noop.py@noop",  # task from a file relative to cwd
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
