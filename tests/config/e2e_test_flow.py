from inspect_flow import FlowJob, FlowOptions, tasks_matrix
from inspect_flow._types.flow_types import FlowDependencies

FlowJob(
    log_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=FlowDependencies(
        additional_dependencies=[
            "./tests/config/local_eval",
        ]
    ),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from a package
            "local_eval/src/local_eval/noop.py@noop",  # task from a file relative to the config
            "tests/config/local_eval/src/local_eval/noop.py@noop",  # task from a file relative to cwd
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
