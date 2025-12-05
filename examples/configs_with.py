from inspect_ai.model import GenerateConfig
from inspect_flow import FlowJob, configs_with, tasks_matrix

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        config=configs_with(
            config=[
                GenerateConfig(temperature=0.0),
                GenerateConfig(temperature=0.5),
                GenerateConfig(temperature=1.0),
            ],
            max_tokens=1000,  # Same max_tokens for all configs
        ),
    ),
)
