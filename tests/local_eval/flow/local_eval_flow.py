from inspect_flow import FlowOptions, FlowSpec, FlowTask, tasks_matrix
from local_eval import noop2

FlowSpec(
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from the package
            "../src/local_eval/noop.py@noop",  # task from a file relative to the config
            FlowTask(factory=noop2),  # task from an imported function
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
