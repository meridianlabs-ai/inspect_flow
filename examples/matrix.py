from inspect_flow import FlowSpec, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            "inspect_evals/gpqa_diamond",
            "inspect_evals/mmlu_0_shot",
        ],
        model=[
            "openai/gpt-5",
            "openai/gpt-5-mini",
        ],
    ),
)
