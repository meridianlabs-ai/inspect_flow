from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowJob, FlowTask

FlowJob(
    defaults=FlowDefaults(config=GenerateConfig(temperature=0.8, max_tokens=1000)),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
            config=GenerateConfig(temperature=0.5, max_tokens=None),
        )
    ],
)
# Result: Task runs with temperature=0.5, max_tokens=1000
# The max_tokens=None didn't override the default 1000
