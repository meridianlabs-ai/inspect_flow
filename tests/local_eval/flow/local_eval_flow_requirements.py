from inspect_flow import FlowDependencies, FlowOptions, FlowSpec, tasks_matrix

FlowSpec(
    log_dir="logs/flow_test",
    log_dir_create_unique=True,
    dependencies=FlowDependencies(dependency_file="../requirements.txt"),
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from the package
        ],
        model=["mockllm/mock-llm1"],
    ),
)
