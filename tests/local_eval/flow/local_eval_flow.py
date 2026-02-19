from inspect_flow import FlowOptions, FlowSpec, FlowTask, tasks_matrix
from inspect_flow._types.flow_types import FlowAgent
from local_eval import add, my_agent, noop2

FlowSpec(
    store=None,
    options=FlowOptions(limit=1),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from the package
            "../src/local_eval/noop.py@noop",  # task from a file relative to the config
            FlowTask(
                factory=noop2,
                solver=FlowAgent(factory=my_agent, args={"tools": [add()]}),
            ),  # task from an imported function
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
    ),
)
