from inspect_flow import FlowJob, FlowTask, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            FlowTask(name="task1", args={"subset": "test"}),  # Single task
            *tasks_matrix(  # Unpacks list of 3 tasks
                task="task2",
                args=[
                    {"language": "en"},
                    {"language": "de"},
                    {"language": "fr"},
                ],
            ),
        ],  # Total: 1 + 3 = 4 tasks
        model=["model1", "model2"],
    ),
)
