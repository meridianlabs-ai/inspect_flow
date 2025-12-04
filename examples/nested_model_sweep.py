from inspect_ai.model import GenerateConfig
from inspect_flow import FlowJob, models_matrix, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task=["inspect_evals/mmlu_0_shot", "inspect_evals/gpqa_diamond"],
        model=[
            "anthropic/claude-3-5-sonnet",  # Single model
            *models_matrix(  # Unpacks list of 4 model configs
                model=["openai/gpt-4o", "openai/gpt-4o-mini"],
                config=[
                    GenerateConfig(reasoning_effort="low"),
                    GenerateConfig(reasoning_effort="high"),
                ],
            ),
        ],  # Total: 1 + 4 = 5 models
    ),
)
