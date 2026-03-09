from inspect_flow import FlowSpec, FlowTask, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=FlowTask(name="inspect_evals/mmlu_0_shot", model="openai/gpt-4o"),
        message_limit=[50, 100],
        cost_limit=[0.01, 0.05],
    ),
)
