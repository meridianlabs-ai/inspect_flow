from inspect_flow import FlowSpec, agents_matrix, tasks_matrix

FlowSpec(
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
