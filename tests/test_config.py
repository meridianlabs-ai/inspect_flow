from pathlib import Path

import yaml
from inspect_ai.model import GenerateConfig
from inspect_flow import flow_task, models_matrix, tasks_matrix, tasks_with
from inspect_flow._config.config import _apply_overrides, load_config
from inspect_flow._types.flow_types import FConfig
from inspect_flow.types import (
    FlowConfig,
    FlowModel,
    FlowOptions,
    FlowTask,
)
from pydantic_core import to_jsonable_python

from tests.test_helpers.type_helpers import fc

update_examples = False


def write_flow_yaml(config: FlowConfig | FConfig, file_path: Path) -> None:
    config = FConfig.model_validate(to_jsonable_python(config))
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
    config = FConfig.model_validate(to_jsonable_python(config))
    # Load the example config file
    example_path = Path(__file__).parents[1] / "examples" / file_name
    with open(example_path, "r") as f:
        expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = config.model_dump(
        mode="json", exclude_unset=True, exclude_defaults=True, exclude_none=True
    )
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
            task={"name": "inspect_evals/mmlu_0_shot"},
            model=[
                FlowModel(name="openai/gpt-4o-mini"),
                FlowModel(name="openai/gpt-5-nano"),
            ],
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
            task=["inspect_evals/mmlu_0_shot", "inspect_evals/mmlu_5_shot"],
            model=["openai/gpt-4o-mini", "openai/gpt-5-nano"],
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
            task=["inspect_evals/mmlu_0_shot", "inspect_evals/mmlu_5_shot"],
            model=[
                "openai/gpt-4o-mini",
                *models_matrix(
                    model={"name": "openai/gpt-5-nano"},
                    config=[
                        GenerateConfig(reasoning_effort="minimal"),
                        GenerateConfig(reasoning_effort="low"),
                    ],
                ),
            ],
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
                task="inspect_evals/mmlu_0_shot",
                model=["openai/gpt-4o-mini", "openai/gpt-5-nano"],
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
            task=[
                FlowTask(
                    name="inspect_evals/mmlu_0_shot",
                    args={"language": "EN_US"},
                ),
                *tasks_matrix(
                    task="inspect_evals/mmlu_5_shot",
                    args=[
                        {"language": "EN_US"},
                        {"language": "CN_CN"},
                        {"language": "DE_DE"},
                    ],
                ),
            ],
            model=["openai/gpt-4o-mini", "openai/gpt-5-nano"],
        ),
    )
    validate_config(config, "nested_matrix_flow.yaml")


def test_merge_config():
    config = FlowConfig(
        flow_dir="./logs/flow_test",
        options=FlowOptions(limit=1),
        dependencies=[
            "./examples/local_eval",
        ],
        tasks=tasks_with(
            task=tasks_matrix(
                task=[
                    "local_eval/noop",
                    FlowTask(
                        "local_eval/noop2",
                        config=GenerateConfig(system_message="Be concise."),
                    ),
                ],
                config=[
                    GenerateConfig(reasoning_effort="low"),
                    GenerateConfig(reasoning_effort="high"),
                ],
            ),
            config=GenerateConfig(max_connections=10),
            model="mockllm/mock-llm1",
        ),
    )
    validate_config(config, "config_merge_flow.yaml")


def test_load_config_overrides():
    config = load_config(
        str(Path(__file__).parents[1] / "examples" / "model_and_task_flow.py"),
        overrides=[
            "flow_dir=./logs/overridden_flow",
            "options.limit=2",
            "defaults.solver.args.tool_calls=none",
        ],
    )
    assert config.flow_dir == "./logs/overridden_flow"
    assert config.options
    assert config.options.limit == 2
    assert config.defaults
    assert config.defaults.solver
    assert config.defaults.solver.args
    assert config.defaults.solver.args["tool_calls"] == "none"


def test_overrides_of_lists():
    config = FlowConfig()
    # Within a single override, later values replace earlier ones
    config = _apply_overrides(
        fc(config),
        [
            "dependencies=dep1",
            "dependencies=dep2",
        ],
    )
    assert config.dependencies == ["dep2"]
    # Within a single override, later values replace earlier ones - even when the type is already a list
    config = _apply_overrides(
        fc(config),
        [
            "dependencies=dep3",
            "dependencies=dep4",
        ],
    )
    assert config.dependencies == ["dep2", "dep4"]
    # Can set a list directly
    config = _apply_overrides(
        fc(config),
        [
            'dependencies=["new_dep1", "new_dep2"]',
        ],
    )
    assert config.dependencies == ["new_dep1", "new_dep2"]
    # There is no way to append multiple values to a list via overrides


def test_overrides_of_dicts():
    config = FlowConfig()
    config = _apply_overrides(
        fc(config),
        [
            "options.metadata.key1=val1",
            "options.metadata.key2=val2",
        ],
    )
    assert config.options and config.options.metadata
    assert config.options.metadata["key1"] == "val1"
    assert config.options.metadata["key2"] == "val2"
    config = _apply_overrides(
        fc(config),
        [
            "options.metadata.key1=val1_updated",
            "options.metadata.key3=val3",
        ],
    )
    assert config.options and config.options.metadata
    assert config.options.metadata["key1"] == "val1_updated"
    assert config.options.metadata["key2"] == "val2"
    assert config.options.metadata["key3"] == "val3"
    # Can set a dict directly
    config = _apply_overrides(
        fc(config),
        [
            'options.metadata={"new_key1": "new_val1", "new_key2": "new_val2"}',
        ],
    )
    assert config.options and config.options.metadata
    assert config.options.metadata["new_key1"] == "new_val1"
    assert config.options.metadata["new_key2"] == "new_val2"
    assert "key1" not in config.options.metadata
