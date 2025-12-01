from inspect_flow import FlowJob, FlowOptions, tasks_matrix
from inspect_flow._types.flow_types import FlowDependencies

FlowJob(
    log_dir="./logs/flow_test",
    log_dir_create_unique=True,
    options=FlowOptions(limit=1),
    dependencies=FlowDependencies(
        additional_dependencies=[
            "../local_eval",
        ]
    ),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from a package
            "../local_eval/src/local_eval/noop.py@noop",  # task from a file relative to the config
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
