from inspect_flow import (
    FlowJob,
    configs_matrix,
    tasks_matrix,
    tasks_with,
)

FlowJob(
    log_dir="logs",
    tasks=tasks_with(
        task=tasks_matrix(
            task=["task1", "task2"], config=configs_matrix(temperature=[0.0, 0.5, 1.0])
        ),  # Creates 6 tasks (2 × 3)
        model="openai/gpt-4o",  # Applied to all 6 tasks
        sandbox="docker",  # Applied to all 6 tasks
    ),
)
