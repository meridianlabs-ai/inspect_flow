from inspect_flow import FlowJob, solvers_matrix, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=solvers_matrix(
            solver="chain_of_thought",
            args=[
                {"max_iterations": 3},
                {"max_iterations": 5},
                {"max_iterations": 10},
            ],
        ),
    ),
)
