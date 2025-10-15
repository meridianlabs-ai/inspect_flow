from pathlib import Path

import yaml
from inspect_flow._config.config import load_config
from inspect_flow._types.types import (
    Dependency,
    FlowConfig,
    FlowOptions,
    Matrix,
    ModelConfig,
    Task,
)

update_examples = False


def write_flow_yaml(config: FlowConfig, file_path: Path) -> None:
    with open(file_path, "w") as f:
        yaml.dump(
            config.model_dump(mode="json", exclude_unset=True),
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def validate_config(config: FlowConfig, file_name: str) -> None:
    # Load the example config file
    example_path = Path(__file__).parent.parent / "examples" / file_name
    with open(example_path) as f:
        expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = config.model_dump(mode="json", exclude_unset=True)
    if update_examples and generated_config != expected_config:
        write_flow_yaml(config, example_path)
    else:
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


def test_config_one_task() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        matrix=Matrix(tasks=Task(name="inspect_evals/mmlu_0_shot")),
    )
    validate_config(config, "one_task_flow.yaml")


def test_config_two_tasks() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        matrix=Matrix(
            tasks=[
                Task(name="inspect_evals/mmlu_0_shot"),
                Task(name="inspect_evals/mmlu_5_shot"),
            ]
        ),
    )
    validate_config(config, "two_task_flow.yaml")


def test_config_two_models_one_task() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        matrix=Matrix(
            tasks=Task(name="inspect_evals/mmlu_0_shot"),
            models=[
                ModelConfig(name="openai/gpt-4o-mini"),
                ModelConfig(name="openai/gpt-5-nano"),
            ],
        ),
    )
    validate_config(config, "two_models_one_task_flow.yaml")


def test_config_two_models_two_tasks() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        matrix=Matrix(
            tasks=[
                Task(name="inspect_evals/mmlu_0_shot"),
                Task(name="inspect_evals/mmlu_5_shot"),
            ],
            models=[
                ModelConfig(name="openai/gpt-4o-mini"),
                ModelConfig(name="openai/gpt-5-nano"),
            ],
        ),
    )
    validate_config(config, "two_models_two_tasks_flow.yaml")


def test_config_matrix_and_task() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        matrix=Matrix(
            tasks=[
                Task(
                    name="inspect_evals/mmlu_0_shot",
                    models=[
                        ModelConfig(name="openai/gpt-4o-mini"),
                        ModelConfig(name="openai/gpt-5-nano"),
                    ],
                ),
                Task(name="inspect_evals/mmlu_5_shot"),
            ],
        ),
    )
    validate_config(config, "matrix_and_task_flow.yaml")


def test_config_nested_matrix() -> None:
    config = FlowConfig(
        options=FlowOptions(log_dir="example_logs", limit=1),
        dependencies=Dependency(
            package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ),
        matrix=Matrix(
            tasks=[
                Task(
                    name="inspect_evals/mmlu_0_shot",
                    args={"language": "EN_US"},
                ),
                Task(
                    name="inspect_evals/mmlu_5_shot",
                    args=[
                        {"language": "EN_US"},
                        {"language": "CN_CN"},
                        {"language": "DE_DE"},
                    ],
                ),
            ],
            models=[
                ModelConfig(name="openai/gpt-4o-mini"),
                ModelConfig(name="openai/gpt-5-nano"),
            ],
        ),
    )
    validate_config(config, "nested_matrix_flow.yaml")
