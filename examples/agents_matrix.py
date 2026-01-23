from inspect_ai.tool import bash, python, web_search
from inspect_flow import FlowSpec, agents_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=agents_matrix(
            agent="react",
            args=[
                {"tools": [web_search()]},
                {"tools": [bash(), python()]},
                {"tools": [web_search(), bash(), python()]},
            ],
        ),
    ),
)
