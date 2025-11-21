from inspect_flow import FlowGenerateConfig, FlowJob, models_matrix, tasks_matrix

FlowJob(
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
                FlowGenerateConfig(reasoning_effort="minimal"),
                FlowGenerateConfig(reasoning_effort="low"),
                FlowGenerateConfig(reasoning_effort="medium"),
                FlowGenerateConfig(reasoning_effort="high"),
            ],
        ),
    ),
)
