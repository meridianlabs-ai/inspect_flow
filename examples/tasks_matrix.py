from inspect_flow import FlowJob, tasks_matrix

FlowJob(
    log_dir="logs",
    dependencies=["inspect-evals"],
    tasks=tasks_matrix(
        task=["inspect_evals/gpqa_diamond", "inspect_evals/mmlu_0_shot"],
        model=["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    ),
)
