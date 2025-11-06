from pathlib import Path

from inspect_flow.types import (
    FlowConfig,
    FlowDefaults,
    FlowModel,
    FlowTask,
    GenerateConfig,
)

config_system_message = "Config System Message"
task_system_message = "Task System Message"
model_system_message = "Model System Message"
config_temperature = 0.0
task_temperature = 0.2
config_max_tokens = 100

task_dir = (Path("examples") / "local_eval" / "src" / "local_eval").resolve()
task_file = str(task_dir / "noop.py")

FlowConfig(
    flow_dir="test_log_dir",
    defaults=FlowDefaults(
        config=GenerateConfig(
            system_message=config_system_message,
            temperature=config_temperature,
            max_tokens=config_max_tokens,
        ),
    ),
    tasks=[
        FlowTask(
            name=task_file,
            config=GenerateConfig(
                system_message=task_system_message,
                temperature=task_temperature,
            ),
            model=FlowModel(
                name="mockllm/mock-llm",
                config=GenerateConfig(system_message=model_system_message),
            ),
        )
    ],
)
