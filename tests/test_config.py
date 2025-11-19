from pathlib import Path

import pytest
import yaml
from inspect_flow import (
    FlowAgent,
    FlowGenerateConfig,
    FlowInclude,
    FlowJob,
    FlowModel,
    FlowOptions,
    FlowSolver,
    FlowTask,
    models_matrix,
    tasks_matrix,
    tasks_with,
)
from inspect_flow._config.load import _apply_overrides, expand_includes, load_config
from pydantic_core import to_jsonable_python

update_examples = True


def write_flow_yaml(config: FlowJob | FlowJob, file_path: Path) -> None:
    config = FlowJob.model_validate(to_jsonable_python(config))
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


def validate_config(config: FlowJob | FlowJob, file_name: str) -> None:
    config = FlowJob.model_validate(to_jsonable_python(config))
    # Load the example config file
    example_path = Path(__file__).parent / "config" / file_name
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
    config = FlowJob(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=[FlowTask(name="inspect_evals/mmlu_0_shot")],
    )
    validate_config(config, "one_task_flow.yaml")


def test_config_two_tasks() -> None:
    config = FlowJob(
        log_dir="example_logs",
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
    config = FlowJob(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        dependencies=[
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=tasks_matrix(
            task=FlowTask(name="inspect_evals/mmlu_0_shot"),
            model=[
                FlowModel(name="openai/gpt-4o-mini"),
                FlowModel(name="openai/gpt-5-nano"),
            ],
        ),
    )
    validate_config(config, "two_models_one_task_flow.yaml")


def test_config_model_and_task() -> None:
    config = FlowJob(
        log_dir="logs/model_and_task",
        options=FlowOptions(limit=1),
        dependencies=[
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        tasks=[FlowTask(name="inspect_evals/mmlu_0_shot", model="openai/gpt-4o-mini")],
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_py_config() -> None:
    config = load_config(
        str(Path(__file__).parent / "config" / "model_and_task_flow.py")
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_py_config_with_assign() -> None:
    config = load_config(
        str(Path(__file__).parent / "config" / "model_and_task2_flow.py")
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_config_two_models_two_tasks() -> None:
    config = FlowJob(
        log_dir="example_logs",
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
    config = FlowJob(
        log_dir="example_logs",
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
                    model=FlowModel(name="openai/gpt-5-nano"),
                    config=[
                        FlowGenerateConfig(reasoning_effort="minimal"),
                        FlowGenerateConfig(reasoning_effort="low"),
                    ],
                ),
            ],
        ),
    )
    validate_config(config, "model_config_flow.yaml")


def test_config_matrix_and_task() -> None:
    config = FlowJob(
        log_dir="example_logs",
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
    config = FlowJob(
        log_dir="example_logs",
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
    config = FlowJob(
        log_dir="./logs/flow_test",
        options=FlowOptions(limit=1),
        dependencies=[
            "./tests/config/local_eval",
        ],
        tasks=tasks_with(
            task=tasks_matrix(
                task=[
                    "local_eval/noop",
                    FlowTask(
                        name="local_eval/noop2",
                        config=FlowGenerateConfig(system_message="Be concise."),
                    ),
                ],
                config=[
                    FlowGenerateConfig(reasoning_effort="low"),
                    FlowGenerateConfig(reasoning_effort="high"),
                ],
            ),
            config=FlowGenerateConfig(max_connections=10),
            model="mockllm/mock-llm1",
        ),
    )
    validate_config(config, "config_merge_flow.yaml")


def test_load_config_overrides():
    config = load_config(
        str(Path(__file__).parent / "config" / "model_and_task_flow.py"),
        overrides=[
            "log_dir=./logs/overridden_flow",
            "options.limit=2",
            "defaults.solver.args.tool_calls=none",
        ],
    )
    assert config.log_dir == "./logs/overridden_flow"
    assert config.options
    assert config.options.limit == 2
    assert config.defaults
    assert config.defaults.solver
    assert config.defaults.solver.args
    assert config.defaults.solver.args["tool_calls"] == "none"


def test_overrides_of_lists():
    config = FlowJob()
    # Within a single override, later values replace earlier ones
    config = _apply_overrides(
        config,
        [
            "dependencies=dep1",
            "dependencies=dep2",
        ],
    )
    assert config.dependencies == ["dep2"]
    # Within a single override, later values replace earlier ones - even when the type is already a list
    config = _apply_overrides(
        config,
        [
            "dependencies=dep3",
            "dependencies=dep4",
        ],
    )
    assert config.dependencies == ["dep2", "dep4"]
    # Can set a list directly
    config = _apply_overrides(
        config,
        [
            'dependencies=["new_dep1", "new_dep2"]',
        ],
    )
    assert config.dependencies == ["new_dep1", "new_dep2"]
    # There is no way to append multiple values to a list via overrides


def test_overrides_of_dicts():
    config = FlowJob()
    config = _apply_overrides(
        config,
        [
            "options.metadata.key1=val1",
            "options.metadata.key2=val2",
        ],
    )
    assert config.options and config.options.metadata
    assert config.options.metadata["key1"] == "val1"
    assert config.options.metadata["key2"] == "val2"
    config = _apply_overrides(
        config,
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
        config,
        [
            'options.metadata={"new_key1": "new_val1", "new_key2": "new_val2"}',
        ],
    )
    assert config.options and config.options.metadata
    assert config.options.metadata["new_key1"] == "new_val1"
    assert config.options.metadata["new_key2"] == "new_val2"
    assert "key1" not in config.options.metadata


def test_load_config_flow_vars():
    config = load_config(
        str(Path(__file__).parent / "config" / "flow_vars_flow.py"),
        flow_vars={"model": "model_from_flow_vars"},
    )
    assert config.tasks
    assert isinstance(config.tasks[0], FlowTask)
    assert config.tasks[0].model
    assert config.tasks[0].model_name == "model_from_flow_vars"


def test_metadata():
    models = [
        FlowModel(name="mockllm/mock-llm1", flow_metadata={"context_window": 1024}),
        FlowModel(name="mockllm/mock-llm2", flow_metadata={"context_window": 2048}),
    ]
    models_to_use = [
        m
        for m in models
        if m.flow_metadata and m.flow_metadata.get("context_window", 0) >= 2000
    ]
    assert len(list(models_to_use)) == 1
    agent = FlowAgent(name="agentname", flow_metadata={"agent": "1"})
    solver = FlowSolver(name="solvername", flow_metadata={"solver": "2"})
    task = FlowTask(name="taskname", flow_metadata={"task": "3"})
    config = FlowJob(
        tasks=tasks_matrix(
            task=task,
            model=models_to_use,
            solver=[solver, agent],
        ),
        flow_metadata={"config": "4"},
    )
    validate_config(config, "metadata_flow.yaml")


def test_overrides_invalid_config_key():
    config = FlowJob()
    with pytest.raises(ValueError):
        config = _apply_overrides(
            config,
            [
                "defaults.config.key1=val1",
            ],
        )


def test_absolute_include() -> None:
    include_path = str(Path(__file__).parent / "config" / "model_and_task_flow.py")
    job = expand_includes(
        FlowJob(includes=[FlowInclude(config_file_path=include_path)])
    )
    validate_config(job, "absolute_include_flow.yaml")


def test_recursive_include() -> None:
    include_path = str(Path(__file__).parent / "config" / "include_flow.py")
    job = expand_includes(
        FlowJob(includes=[FlowInclude(config_file_path=include_path)])
    )
    validate_config(job, "recursive_include_flow.yaml")


def test_multiple_includes() -> None:
    job = expand_includes(
        FlowJob(
            includes=[
                "defaults_flow.py",
                "e2e_test_flow.py",
                "model_and_task_flow.py",
            ]
        ),
        base_path=str(Path(__file__).parent / "config"),
    )
    validate_config(job, "multiple_includes_flow.yaml")
