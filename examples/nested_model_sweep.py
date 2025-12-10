from inspect_ai.model import GenerateConfig
from inspect_flow import FlowJob, models_matrix, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task=["inspect_evals/mmlu_0_shot", "inspect_evals/gpqa_diamond"],
        model=[  # <1>
            "anthropic/claude-3-5-sonnet",  # <2>
            *models_matrix(  # <3>
                model=["openai/gpt-4o", "openai/gpt-4o-mini"],
                config=[
                    GenerateConfig(reasoning_effort="low"),
                    GenerateConfig(reasoning_effort="high"),
                ],
            ),
        ],
    ),
)
