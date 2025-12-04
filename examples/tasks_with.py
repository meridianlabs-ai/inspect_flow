from inspect_ai.model import GenerateConfig
from inspect_flow import FlowJob, tasks_with

FlowJob(
    tasks=tasks_with(
        task=["inspect_evals/gpqa_diamond", "inspect_evals/mmlu_0_shot"],
        model="openai/gpt-4o",  # Same model for both tasks
        config=GenerateConfig(temperature=0.7),  # Same config for both
    )
)
