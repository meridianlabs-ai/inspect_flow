from inspect_flow import FlowJob, solvers_with, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=solvers_with(
            solver=["chain_of_thought", "plan_solve", "self_critique"],
            args={"max_steps": 5},
        ),
    ),
)
