from pathlib import Path

import yaml
from inspect_ai.model import GenerateConfig
from inspect_flow import flow_task, models_matrix, tasks_matrix
from inspect_flow._config.config import load_config
from inspect_flow._types.flow_types import FConfig
from inspect_flow.types import (
    FlowConfig,
    FlowModel,
    FlowOptions,
    FlowTask,
)

update_examples = False


def write_flow_yaml(config: FlowConfig | FConfig, file_path: Path) -> None:
    with open(file_path, "w") as f:
        yaml.dump(
            config.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_defaults=True,
                exclude_none=True,
            ),
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def validate_config(config: FlowConfig | FConfig, file_name: str) -> None:
    # Load the example config file
    example_path = Path(__file__).parents[1] / "examples" / file_name
    with open(example_path, "r") as f:
        expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = config.model_dump(mode="json", exclude_unset=True)
    if update_examples and generated_config != expected_config:
        write_flow_yaml(config, example_path)
    else:
        assert generated_config == expected_config


def test_config_one_task() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=[FlowTask(name="inspect_evals/mmlu_0_shot")],
    )
    validate_config(config, "one_task_flow.yaml")


def test_config_two_tasks() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=[
            FlowTask(name="inspect_evals/mmlu_0_shot"),
            FlowTask(name="inspect_evals/mmlu_5_shot"),
        ],
    )
    validate_config(config, "two_task_flow.yaml")


def test_config_two_models_one_task() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=tasks_matrix(
            {"name": "inspect_evals/mmlu_0_shot"},
            {
                "model": [
                    FlowModel(name="openai/gpt-4o-mini"),
                    FlowModel(name="openai/gpt-5-nano"),
                ],
            },
        ),
    )
    validate_config(config, "two_models_one_task_flow.yaml")


def test_config_model_and_task() -> None:
    config = FlowConfig(
        flow_dir="logs/model_and_task",
        options=FlowOptions(limit=1),
        dependencies=[
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=[
            flow_task(
                {"name": "inspect_evals/mmlu_0_shot", "model": "openai/gpt-4o-mini"}
            )
        ],
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_py_config() -> None:
    config = load_config(
        str(Path(__file__).parents[1] / "examples" / "model_and_task_flow.py")
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_py_config_with_assign() -> None:
    config = load_config(
        str(Path(__file__).parents[1] / "examples" / "model_and_task2_flow.py")
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_config_two_models_two_tasks() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=tasks_matrix(
            ["inspect_evals/mmlu_0_shot", "inspect_evals/mmlu_5_shot"],
            {
                "model": ["openai/gpt-4o-mini", "openai/gpt-5-nano"],
            },
        ),
    )
    validate_config(config, "two_models_two_tasks_flow.yaml")


def test_config_model_config() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=tasks_matrix(
            ["inspect_evals/mmlu_0_shot", "inspect_evals/mmlu_5_shot"],
            {
                "model": [
                    "openai/gpt-4o-mini",
                    *models_matrix(
                        {"name": "openai/gpt-5-nano"},
                        {
                            "config": [
                                GenerateConfig(reasoning_effort="minimal"),
                                GenerateConfig(reasoning_effort="low"),
                            ],
                        },
                    ),
                ],
            },
        ),
    )
    validate_config(config, "model_config_flow.yaml")


def test_config_matrix_and_task() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=[
            *tasks_matrix(
                "inspect_evals/mmlu_0_shot",
                {
                    "model": ["openai/gpt-4o-mini", "openai/gpt-5-nano"],
                },
            ),
            FlowTask(name="inspect_evals/mmlu_5_shot"),
        ],
    )
    validate_config(config, "matrix_and_task_flow.yaml")


def test_config_nested_matrix() -> None:
    config = FlowConfig(
        flow_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=tasks_matrix(
            [
                FlowTask(
                    name="inspect_evals/mmlu_0_shot",
                    args={"language": "EN_US"},
                ),
                *tasks_matrix(
                    "inspect_evals/mmlu_5_shot",
                    {
                        "args": [
                            {"language": "EN_US"},
                            {"language": "CN_CN"},
                            {"language": "DE_DE"},
                        ],
                    },
                ),
            ],
            {
                "model": ["openai/gpt-4o-mini", "openai/gpt-5-nano"],
            },
        ),
    )
    validate_config(config, "nested_matrix_flow.yaml")
