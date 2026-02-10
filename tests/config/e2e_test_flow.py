from inspect_flow import FlowOptions, FlowSpec, tasks_matrix
from inspect_flow._types.flow_types import FlowDependencies

FlowSpec(
    log_dir="s3://inspect-flow-test/metr",
    log_dir_create_unique=False,
    options=FlowOptions(
        limit=1, retry_wait=1, retry_attempts=2, log_dir_allow_dirty=True
    ),
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
