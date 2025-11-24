from inspect_flow import FlowGenerateConfig, FlowJob, tasks_with

FlowJob(
    tasks=tasks_with(
        task=["inspect_evals/gpqa_diamond", "inspect_evals/mmlu_0_shot"],
        model="openai/gpt-4o",  # Same model for both tasks
        config=FlowGenerateConfig(temperature=0.7),  # Same config for both
    )
)
