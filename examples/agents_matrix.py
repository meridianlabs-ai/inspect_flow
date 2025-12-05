from inspect_flow import FlowJob, agents_matrix, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=agents_matrix(
            agent="system_message",
            args=[
                {"message": "You are a helpful assistant."},
                {"message": "You are a creative writer."},
                {"message": "You are a technical expert."},
            ],
        ),
    ),
)
