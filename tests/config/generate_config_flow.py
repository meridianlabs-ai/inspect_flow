from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowJob, FlowModel, FlowTask

FlowJob(
    log_dir="logs/flow",
    defaults=FlowDefaults(config=GenerateConfig(temperature=0.7)),
    tasks=[
        FlowTask(
            name="../local_eval/src/local_eval/noop.py@noop",
            config=GenerateConfig(max_tokens=500),
            model=FlowModel(
                name="mockllm/mock-llm",
                config=GenerateConfig(reasoning_effort="medium"),
            ),
        )
    ],
)
