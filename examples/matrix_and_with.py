from inspect_flow import (
    FlowJob,
    configs_matrix,
    tasks_matrix,
    tasks_with,
)

FlowJob(
    log_dir="logs",
    tasks=tasks_with(
        task=tasks_matrix(  # <1>
            task=["task1", "task2"],  # <1>
            config=configs_matrix(  # <1>
                temperature=[0.0, 0.5, 1.0],  # <1>
            ),  # <1>
        ),  # <1>
        model="openai/gpt-4o",  # <2>
        sandbox="docker",  # <3>
    ),
)
