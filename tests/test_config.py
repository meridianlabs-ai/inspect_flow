from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai._util.logger import LogHandlerVar
from inspect_ai._util.registry import registry_value
from inspect_ai.model import CachePolicy, GenerateConfig
from inspect_flow import (
    FlowAgent,
    FlowModel,
    FlowOptions,
    FlowSolver,
    FlowSpec,
    FlowTask,
    models_matrix,
    tasks_matrix,
    tasks_with,
)
from inspect_flow._api.api import load_spec
from inspect_flow._config.defaults import apply_defaults
from inspect_flow._config.load import (
    ConfigOptions,
    LoadState,
    _apply_auto_includes,
    _apply_overrides,
    _apply_substitutions,
    _log_dir_create_unique,
    expand_spec,
    int_load_spec,
)
from inspect_flow._types.flow_types import FlowDependencies
from inspect_flow._util.logging import init_flow_logging
from pydantic import ValidationError

from tests.local_eval.src.local_eval.tools import add
from tests.test_helpers.config_helpers import validate_config

config_dir = str(Path(__file__).parent / "config")


def test_config_one_task() -> None:
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        tasks=[FlowTask(name="inspect_evals/mmlu_0_shot")],
    )
    validate_config(config, "one_task_flow.yaml")


def test_config_two_tasks() -> None:
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        tasks=[
            FlowTask(name="inspect_evals/mmlu_0_shot"),
            FlowTask(name="inspect_evals/mmlu_5_shot"),
        ],
    )
    validate_config(config, "two_task_flow.yaml")


def test_config_two_models_one_task() -> None:
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
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
    config = FlowSpec(
        log_dir="logs/model_and_task",
        options=FlowOptions(limit=1),
        tasks=[FlowTask(name="inspect_evals/mmlu_0_shot", model="openai/gpt-4o-mini")],
    )
    spec = apply_defaults(config)
    validate_config(spec, "model_and_task_flow.yaml")


def test_py_config() -> None:
    config = load_spec(str(Path(__file__).parent / "config" / "model_and_task_flow.py"))
    validate_config(config, "model_and_task_flow.yaml")


def test_py_config_with_assign() -> None:
    config = load_spec(
        str(Path(__file__).parent / "config" / "model_and_task2_flow.py")
    )
    validate_config(config, "model_and_task_flow.yaml")


def test_config_two_models_two_tasks() -> None:
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        tasks=tasks_matrix(
            task=["inspect_evals/mmlu_0_shot", "inspect_evals/mmlu_5_shot"],
            model=["openai/gpt-4o-mini", "openai/gpt-5-nano"],
        ),
    )
    validate_config(config, "two_models_two_tasks_flow.yaml")


def test_config_model_config() -> None:
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        tasks=tasks_matrix(
            task=["inspect_evals/mmlu_0_shot", "inspect_evals/mmlu_5_shot"],
            model=[
                "openai/gpt-4o-mini",
                *models_matrix(
                    model=FlowModel(name="openai/gpt-5-nano"),
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
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
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
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
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
    config = FlowSpec(
        log_dir="./logs/flow_test",
        options=FlowOptions(limit=1),
        tasks=tasks_with(
            task=tasks_matrix(
                task=[
                    "local_eval/noop",
                    FlowTask(
                        name="local_eval/noop2",
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
    config = int_load_spec(
        str(Path(__file__).parent / "config" / "model_and_task_flow.py"),
        options=ConfigOptions(
            overrides=[
                "log_dir=./logs/overridden_flow",
                "options.limit=2",
                "defaults.solver.args.tool_calls=none",
            ]
        ),
    )
    assert config.log_dir == "./logs/overridden_flow"
    assert config.options
    assert config.options.limit == 2
    assert config.defaults
    assert config.defaults.solver
    assert config.defaults.solver.args
    assert config.defaults.solver.args["tool_calls"] == "none"


def test_overrides_of_lists():
    config = FlowSpec()
    # Within a single override, later values replace earlier ones
    config = _apply_overrides(
        config,
        [
            "dependencies.additional_dependencies=dep1",
            "dependencies.additional_dependencies=dep2",
        ],
    )
    assert config.dependencies
    assert config.dependencies.additional_dependencies == "dep2"
    config.dependencies.additional_dependencies = ["dep2"]
    # Within a single override, later values replace earlier ones - even when the type is already a list
    config = _apply_overrides(
        config,
        [
            "dependencies.additional_dependencies=dep3",
            "dependencies.additional_dependencies=dep4",
        ],
    )
    assert config.dependencies
    assert config.dependencies.additional_dependencies == ["dep2", "dep4"]
    # Can set a list directly
    config = _apply_overrides(
        config,
        [
            'dependencies.additional_dependencies=["new_dep1", "new_dep2"]',
        ],
    )
    assert config.dependencies
    assert config.dependencies.additional_dependencies == ["new_dep1", "new_dep2"]
    # There is no way to append multiple values to a list via overrides


def test_overrides_of_dicts():
    config = FlowSpec()
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


def test_load_config_args() -> None:
    config = load_spec(
        str(Path(__file__).parent / "config" / "args_flow.py"),
        args={"model": "model_from_args"},
    )
    assert config.tasks
    assert isinstance(config.tasks[0], FlowTask)
    assert config.tasks[0].model
    assert config.tasks[0].model_name == "model_from_args"


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
    spec = FlowSpec(
        tasks=tasks_matrix(
            task=task,
            model=models_to_use,
            solver=[solver, agent],
        ),
        flow_metadata={"config": "4"},
    )
    validate_config(spec, "metadata_flow.yaml")


def test_overrides_invalid_config_key():
    config = FlowSpec()
    with pytest.raises(ValueError):
        config = _apply_overrides(
            config,
            [
                "defaults.config.key1=val1",
            ],
        )


def test_absolute_include() -> None:
    include_path = str(Path(__file__).parent / "config" / "model_and_task_flow.py")
    spec = expand_spec(
        FlowSpec(includes=[include_path]),
        base_dir=config_dir,
    )
    validate_config(spec, "absolute_include_flow.yaml")


def test_recursive_include() -> None:
    include_path = str(Path(__file__).parent / "config" / "include_flow.py")
    spec = expand_spec(
        FlowSpec(includes=[include_path]),
        base_dir=config_dir,
    )
    validate_config(spec, "recursive_include_flow.yaml")


def test_multiple_includes() -> None:
    spec = expand_spec(
        FlowSpec(
            includes=[
                "defaults_flow.py",
                "dependencies_flow.py",
                "model_and_task_flow.py",
            ]
        ),
        base_dir=config_dir,
    )
    validate_config(spec, "multiple_includes_flow.yaml")


def test_auto_include(capsys) -> None:
    spec = load_spec(
        str(
            Path(__file__).parent / "config" / "auto" / "sub" / "model_and_task_flow.py"
        )
    )
    out = capsys.readouterr().out
    validate_config(spec, "auto_include_flow.yaml")
    # Remove all whitespace from rich console formatting to handle line wrapping
    out_normalized = "".join(out.split())
    assert "model_and_task_flow.py" in out_normalized
    assert "_flow.py" in out_normalized
    assert "_other_flow.py" in out_normalized


def test_auto_include_two(capsys) -> None:
    log_handler: LogHandlerVar = {"handler": None}
    init_flow_logging(log_level="warning", log_handler_var=log_handler)
    spec = load_spec(
        str(
            Path(__file__).parent / "config" / "auto" / "another_flow" / "test_flow.py"
        ),
    )
    out = capsys.readouterr().out
    validate_config(spec, "auto_include_two_flow.yaml")
    # Remove all whitespace from rich console formatting to handle line wrapping
    out_normalized = "".join(out.split())
    assert "auto/_flow.py" in out_normalized
    assert "Applyingmultiple_flow.py.#2:" in out_normalized


def test_216_auto_include_from_sub_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    flow_file = (
        Path(__file__).parent / "config" / "auto" / "sub" / "model_and_task_flow.py"
    )
    monkeypatch.chdir(
        flow_file.parent
    )  # Change to sub-directory to test relative includes
    spec = load_spec("model_and_task_flow.py")
    validate_config(spec, "auto_include_flow.yaml")


def test_219_include_remove_duplicates() -> None:
    include_path = str(Path(__file__).parent / "config" / "dependencies_flow.py")
    spec = expand_spec(
        FlowSpec(
            includes=[include_path],
            dependencies=FlowDependencies(
                additional_dependencies=[
                    "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
                ]
            ),
        ),
        base_dir=config_dir,
    )
    assert spec.dependencies
    assert spec.dependencies.additional_dependencies == [
        "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
    ]  # No duplicates


def test_221_format_map() -> None:
    spec = FlowSpec(
        log_dir="./logs/flow_test",
        options=FlowOptions(limit=1, bundle_dir="{log_dir}/bundle"),
        tasks=tasks_matrix(
            task=[
                "local_eval/noop",
            ],
            model=[
                FlowModel(
                    name="mockllm/mock-llm1",
                ),
            ],
        ),
    )
    spec2 = expand_spec(spec, base_dir=".")
    assert spec2.options
    assert spec2.options.bundle_dir == "./logs/flow_test/bundle"


def test_221_format_map_nested() -> None:
    spec = FlowSpec(
        log_dir="{flow_metadata[dir]}/flow_test",
        flow_metadata={"root": "tests", "dir": "{flow_metadata[root]}/logs"},
    )
    spec2 = expand_spec(spec, base_dir=".")
    assert spec2.log_dir == "tests/logs/flow_test"


def test_221_format_map_recursive() -> None:
    spec = FlowSpec(
        flow_metadata={
            "one": "{flow_metadata[two]}/a",
            "two": "{flow_metadata[one]}/b",
        },
    )
    with pytest.raises(ValueError):
        expand_spec(spec, base_dir=".")


def test_221_format_map_file() -> None:
    include_path = str(Path(__file__).parent / "config" / "bundle_flow.py")
    spec = load_spec(include_path)
    assert spec.options
    assert spec.options.bundle_dir == "logs/bundle_flow/bundle"
    validate_config(spec, "bundle_flow.yaml")


def test_257_format_map_not_config() -> None:
    spec = FlowSpec(
        log_dir="logs/",
        env={
            "INSPECT_EVAL_LOG_FILE_PATTERN": "{log_dir}/{task}_{model}_{id}",
        },
        tasks=tasks_with(
            task=["inspect_evals/mmlu_0_shot"],
            model="openai/gpt-4o-mini",
        ),
    )
    spec2 = expand_spec(spec, base_dir=".")
    assert spec2.log_dir == "logs/"
    assert spec2.env
    assert spec2.env["INSPECT_EVAL_LOG_FILE_PATTERN"] == "logs//{task}_{model}_{id}"


def test_266_format_map_log_dir_create_unique() -> None:
    log_dir = "logs/flow_test"
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    spec = FlowSpec(
        log_dir=log_dir,
        log_dir_create_unique=True,
        options=FlowOptions(limit=1, bundle_dir="{log_dir}/bundle"),
        tasks=tasks_matrix(
            task=[
                "local_eval/noop",
            ],
            model=[
                FlowModel(
                    name="mockllm/mock-llm1",
                ),
            ],
        ),
    )
    spec2 = expand_spec(spec, base_dir=".")
    assert spec2.log_dir != log_dir
    assert spec2.options
    assert spec2.options.bundle_dir == f"{spec2.log_dir}/bundle"


def test_222_including_specs_check() -> None:
    include_path = str(Path(__file__).parent / "config" / "including_specs_flow.py")
    spec = FlowSpec(
        includes=[include_path],
        options=FlowOptions(limit=1),
    )
    spec2 = expand_spec(spec, base_dir=config_dir)
    assert spec2.options
    assert spec2.options.max_samples == 16

    spec3 = FlowSpec(
        includes=[include_path],
        options=FlowOptions(limit=1, max_samples=1024),
    )
    with pytest.raises(ValueError):
        expand_spec(spec3, base_dir=config_dir)


def test_206_dirty_repo_check() -> None:
    include_path = str(Path(__file__).parent / "config" / "dirty_repo_flow.py")
    spec = FlowSpec(
        includes=[include_path],
        options=FlowOptions(limit=1),
    )

    dirty_file = Path(__file__).parent / "test_dirty_file.txt"
    dirty_file.touch()
    try:
        with pytest.raises(RuntimeError):
            spec = expand_spec(spec, base_dir=Path(include_path).parent.as_posix())
    finally:
        dirty_file.unlink()


def test_154_cache_policy() -> None:
    config = FlowSpec(
        tasks=[
            FlowTask(
                name="some_task",
                model=FlowModel(
                    name="some_model",
                    config=GenerateConfig(cache=CachePolicy(expiry="1h")),
                ),
            ),
        ],
    )
    validate_config(config, "cache_policy_flow.yaml")


def test_log_dir_create_unique() -> None:
    with patch("inspect_flow._config.load.exists") as mock_exists:
        mock_exists.return_value = False
        assert _log_dir_create_unique("log_dir") == "log_dir"
        assert mock_exists.call_count == 1
    with patch("inspect_flow._config.load.exists") as mock_exists:
        mock_exists.side_effect = [True, True, False]
        assert _log_dir_create_unique("log_dir") == "log_dir_2"
        assert mock_exists.call_count == 3
    with patch("inspect_flow._config.load.exists") as mock_exists:
        mock_exists.side_effect = [True, True, False]
        assert _log_dir_create_unique("log_dir_12") == "log_dir_14"
        assert mock_exists.call_count == 3


def test_apply_substitutions_log_dir_create_unique() -> None:
    log_dir = "/etc/logs/flow"
    with (
        patch("inspect_flow._config.load.exists") as mock_exists,
    ):
        mock_exists.side_effect = [True, True, False]
        spec = FlowSpec(
            log_dir=log_dir,
            log_dir_create_unique=True,
            tasks=["task_name"],
        )
        spec2 = _apply_substitutions(spec, base_dir=Path.cwd().resolve().as_posix())
        assert spec2.log_dir == f"{log_dir}_2"
    assert mock_exists.call_count == 3


def test_load_invalid() -> None:
    invalid_config_path = str(Path(config_dir) / "invalid_flow.py")
    with pytest.raises(ValidationError) as e:
        load_spec(invalid_config_path)
    assert getattr(e.value, "_flow_handled", False) is True


def test_load_no_spec() -> None:
    config_path = str(Path(config_dir) / "dirty_repo_flow.py")
    with pytest.raises(ValueError) as e:
        load_spec(config_path)
    assert getattr(e.value, "_flow_handled", False) is False


def test_load_yaml() -> None:
    config_path = str(Path(__file__).parent / "expected" / "first_config.yaml")
    spec = load_spec(config_path)
    validate_config(spec, "first_config.yaml")


def test_unsupported_format() -> None:
    config_path = str(Path(__file__).parent.parent / "pyproject.toml")
    with pytest.raises(ValueError) as e:
        load_spec(config_path)
    assert "Unsupported config file extension: .toml" in str(e.value)


def test_not_flow_spec() -> None:
    config_path = str(Path(config_dir) / "not_flow.py")
    with pytest.raises(TypeError) as e:
        load_spec(config_path)
    assert "got <class 'int'>" in str(e.value)


def test_auto_include_protocol() -> None:
    spec1 = FlowSpec()
    spec2 = _apply_auto_includes(
        spec1, base_dir="file://parent/file", options=ConfigOptions(), state=LoadState()
    )
    assert spec1 == spec2


def test_389_tool_config() -> None:
    config = FlowSpec(
        log_dir="example_logs",
        options=FlowOptions(limit=1),
        tasks=[
            FlowTask(
                name="inspect_evals/mmlu_0_shot",
                solver=FlowAgent(
                    name="some_solver",
                    args={"tools": [registry_value(add())]},
                ),
            )
        ],
    )
    validate_config(config, "tool_config_flow.yaml")
