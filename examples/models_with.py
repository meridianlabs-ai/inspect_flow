from inspect_ai.model import GenerateConfig
from inspect_flow import FlowJob, models_with, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        model=models_with(
            model=["openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022"],
            config=GenerateConfig(temperature=0.7),  # Same config for both models
        ),
    ),
)
