from inspect_flow import FlowJob, GenerateConfig, models_matrix, tasks_matrix

FlowJob(
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
            config=[
                GenerateConfig(reasoning_effort="minimal"),
                GenerateConfig(reasoning_effort="low"),
                GenerateConfig(reasoning_effort="medium"),
                GenerateConfig(reasoning_effort="high"),
            ],
        ),
    ),
)
