from inspect_ai.tool import bash, web_search
from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowExtraArgs,
    FlowSpec,
    FlowTask,
)

FlowSpec(
    log_dir="logs",
    defaults=FlowDefaults(
        agent=FlowAgent(
            name="react",
            args={"tools": [web_search()]},  # <1>
        )
    ),
    tasks=[
        FlowTask(name="task1"),  # <2>
        FlowTask(
            name="task2",
            extra_args=FlowExtraArgs(
                agent={"tools": [bash()]}  # <3>
            ),
        ),
    ],
)
