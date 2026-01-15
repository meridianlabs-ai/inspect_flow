from inspect_flow import FlowAgent, FlowOptions, FlowSpec, FlowTask, tasks_matrix

FlowSpec(
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=[
            FlowTask(
                name="local_eval/noop", solver=FlowAgent(name="local_eval/test_agent")
            ),
            "local_eval/noop",  # task from the package
            "../src/local_eval/noop.py@noop",  # task from a file relative to the config
        ],
        # model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
