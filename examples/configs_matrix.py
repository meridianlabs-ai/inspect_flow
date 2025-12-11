from inspect_flow import FlowSpec, configs_matrix, models_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            "inspect_evals/gpqa_diamond",
            "inspect_evals/mmlu_0_shot",
        ],
        model=models_matrix(
            model=[
                "openai/gpt-5",
                "openai/gpt-5-mini",
            ],
            config=configs_matrix(
                reasoning_effort=["minimal", "low", "medium", "high"],
            ),
        ),
    ),
)
