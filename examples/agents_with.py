from inspect_flow import FlowSpec, agents_with, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=agents_with(
            agent=["system_message", "tool_agent", "web_agent"],
            args={"system_message": "You are a helpful assistant."},
        ),
    ),
)
