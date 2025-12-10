from inspect_flow import FlowJob, FlowTask, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            FlowTask(name="task1", args={"subset": "test"}),  # <1>
            *tasks_matrix(  # <2>
                task="task2",  # <3>
                args=[  # <3>
                    {"language": "en"},  # <3>
                    {"language": "de"},  # <3>
                    {"language": "fr"},  # <3>
                ],  # <3>
            ),  # <3>
        ],  # <3>
        model=["model1", "model2"],
    ),
)
