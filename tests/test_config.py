from pathlib import Path

import yaml
from inspect_flow._config.config import load_config
from inspect_flow._types.types import (
    Dependency,
    FlowConfig,
    FlowOptions,
    SingleTask,
)


def write_flow_yaml(config: FlowConfig) -> None:
    # Write config to YAML file in logs directory
    logs_dir = Path("./logs")

    config_output_path = logs_dir / "config.yaml"
    with open(config_output_path, "w") as f:
        yaml.dump(
            config.model_dump(mode="json", exclude_unset=True),
            f,
            default_flow_style=False,
        )


def validate_config(config: FlowConfig, file_name: str) -> None:
    # Load the example config file
    example_path = Path(__file__).parent.parent / "examples" / file_name
    with open(example_path) as f:
        expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = config.model_dump(mode="json", exclude_unset=True)
    assert generated_config == expected_config


def test_load_simple_eval_set() -> None:
    # Load the config file
    config_path = Path(__file__).parent.parent / "examples" / "simple.eval-set.yaml"
    config = load_config(str(config_path))

    # Verify the result
    assert config is not None
    assert config.run is not None
    assert len(config.run.task_groups) == 1
    task_group = config.run.task_groups[0]
    assert task_group.eval_set is not None
    assert len(task_group.eval_set.tasks) == 1
    assert task_group.eval_set.models is not None
    assert len(task_group.eval_set.models) == 1


def test_write_simple_flow() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        tasks=SingleTask(name="inspect_evals/mmlu_0_shot"),
    )
    validate_config(config, "single_task_flow.yaml")
