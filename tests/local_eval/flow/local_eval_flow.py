from inspect_flow import FlowOptions, FlowSpec, tasks_matrix

FlowSpec(
    store=None,
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from the package
            "../src/local_eval/noop.py@noop",  # task from a file relative to the config
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
