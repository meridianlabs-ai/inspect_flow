from inspect_flow import FlowJob, FlowTask, GenerateConfig

FlowJob(
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
            # Override just temperature
            config=GenerateConfig(temperature=0.7),
        ),
    ],
)
# Inherits max_connections=10 from _flow.py
# Overrides temperature=0.7 for this specific task
