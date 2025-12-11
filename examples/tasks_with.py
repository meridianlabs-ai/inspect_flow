from inspect_ai.model import GenerateConfig
from inspect_flow import FlowSpec, tasks_with

FlowSpec(
    tasks=tasks_with(
        task=["inspect_evals/gpqa_diamond", "inspect_evals/mmlu_0_shot"],
        model="openai/gpt-4o",  # <1>
        config=GenerateConfig(temperature=0.7),  # <2>
    )
)
