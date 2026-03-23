import logging
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from botocore.client import BaseClient
from inspect_ai import Task
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.logger import LogHandler, LogHandlerVar, _logHandler
from inspect_ai.agent import Agent
from inspect_ai.approval._policy import ApprovalPolicyConfig, ApproverPolicyConfig
from inspect_ai.model import GenerateConfig, Model, ModelName, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import SandboxEnvironmentSpec
from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowModel,
    FlowOptions,
    FlowSolver,
    FlowSpec,
    FlowStoreConfig,
    FlowTask,
    models_matrix,
    solvers_matrix,
    tasks_matrix,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.flow_types import FlowScorer, not_given
from inspect_flow._util.error import FlowHandledError
from inspect_flow._util.logging import init_flow_logging
from rich.console import Console

from .test_helpers.log_helpers import init_test_logs, init_test_store, verify_test_logs

task_dir = "tests/local_eval/src/local_eval"
task_file = task_dir + "/noop.py"


def test_task_with_get_model(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=log_dir,
                tasks=[
                    FlowTask(
                        name=task_file + "@task_with_get_model",
                        model=FlowModel(name="mockllm/mock-llm"),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    # verify default values
    assert call_args.kwargs["retry_on_error"] == 3
    assert call_args.kwargs["max_tasks"] == 10


def test_task_with_two_models() -> None:
    # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
    # So can not use a mock
    log_dir = init_test_logs()

    spec = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(
            task=task_file + "@noop",
            model=[
                FlowModel(name="mockllm/mock-llm1"),
                FlowModel(name="mockllm/mock-llm2"),
            ],
        ),
    )
    run_eval_set(spec=(spec), base_dir=".")

    verify_test_logs(spec, log_dir)


def test_default_model(
    monkeypatch: pytest.MonkeyPatch, recording_console: Console
) -> None:
    monkeypatch.setenv("INSPECT_EVAL_MODEL", "mockllm/mock-llm")
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=task_file + "@noop")],
    )
    run_eval_set(spec=spec, base_dir=".")
    verify_test_logs(spec, log_dir)
    assert "ERROR" not in recording_console.export_text()


def test_spec_log_level_applied_to_eval_set(recording_console: Console) -> None:
    # Get the handler set up by the autouse init_log_handler fixture. Putting it in
    # _logHandler simulates CLI usage, where a second init_logger call (from eval_set)
    # is a no-op because the handler is already set.
    root_rich_handlers = [
        h for h in logging.getLogger().handlers if isinstance(h, LogHandler)
    ]
    assert root_rich_handlers, "init_log_handler autouse fixture must set up a handler"
    flow_handler = root_rich_handlers[0]

    saved = _logHandler["handler"]
    _logHandler["handler"] = flow_handler
    try:
        log_dir = init_test_logs()
        spec = FlowSpec(
            log_dir=log_dir,
            tasks=[
                FlowTask(
                    name=task_file + "@debug_logging_task",
                    model=FlowModel(name="mockllm/model"),
                )
            ],
            options=FlowOptions(log_level="debug"),
        )
        run_eval_set(spec=spec, base_dir=".")
        assert "flow-spec-log-level-debug-marker" in recording_console.export_text()
    finally:
        _logHandler["handler"] = saved


def test_model_generate_config(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    system_message = "Test System Message"
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=log_dir,
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model=FlowModel(
                            name="mockllm/mock-llm",
                            config=GenerateConfig(system_message=system_message),
                        ),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)
    config = tasks_arg[0].model.config
    assert config.system_message == system_message


def test_task_model(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=log_dir,
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model=FlowModel(name="mockllm/mock-llm"),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)
    assert tasks_arg[0].model.name == "mock-llm"


def test_write_config(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()

    spec = FlowSpec(
        store=None,
        log_dir=log_dir,
        tasks=[
            FlowTask(
                name=task_file + "@noop",
                model=FlowModel(name="mockllm/mock-llm"),
            )
        ],
    )
    run_eval_set(spec=spec, base_dir=".")

    mock_eval_set.assert_called_once()

    config_file = Path(log_dir) / "flow.yaml"
    assert config_file.exists()

    # Read the file, parse the yaml, and convert to FlowSpec
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        loaded_spec = FlowSpec.model_validate(data, extra="forbid")
        assert (
            loaded_spec.python_version
            == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        loaded_spec.python_version = not_given
        assert loaded_spec == spec


def test_matrix_args(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                tasks=tasks_matrix(
                    task=FlowTask(
                        name=task_file + "@task_with_params",
                        model=FlowModel(name="mockllm/mock-llm"),
                    ),
                    args=[{"subset": "original"}, {"subset": "contrast"}],
                ),
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert tasks_arg[0].metadata["subset"] == "original"
    assert tasks_arg[1].metadata["subset"] == "contrast"


def test_matrix_model_roles(mock_eval_set: MagicMock) -> None:
    system_message = "mock system message"
    model_roles1 = {
        "mark": "mockllm/mock-mark1",
        "conartist": "mockllm/mock-conartist1",
    }
    model_roles2 = {
        "mark": "mockllm/mock-mark2",
        "conartist": FlowModel(
            name="mockllm/mock-conartist2",
            config=GenerateConfig(system_message=system_message),
        ),
    }
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                tasks=tasks_matrix(
                    task=FlowTask(
                        name=task_file + "@task_with_model_roles",
                        model=FlowModel(name="mockllm/mock-llm"),
                    ),
                    model_roles=[model_roles1, model_roles2],
                ),
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert tasks_arg[0].model_roles["mark"].name == "mock-mark1"
    assert tasks_arg[0].model_roles["conartist"].name == "mock-conartist1"
    assert tasks_arg[1].model_roles["mark"].name == "mock-mark2"
    assert tasks_arg[1].model_roles["conartist"].name == "mock-conartist2"
    assert tasks_arg[1].model_roles["conartist"].config.system_message == system_message


def test_matrix_solvers(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                tasks=tasks_matrix(
                    task=FlowTask(
                        name=task_file + "@noop",
                        model=FlowModel(name="mockllm/mock-llm"),
                    ),
                    solver=[
                        *solvers_matrix(
                            solver="inspect_ai/system_message",
                            args=[
                                {"template": "test system message"},
                                {"template": "another test system message"},
                            ],
                        ),
                        [
                            FlowSolver(
                                name="inspect_ai/system_message",
                                args={"template": "test system message"},
                            ),
                            FlowSolver(name="inspect_ai/generate"),
                        ],
                        FlowAgent(name="inspect_ai/react"),
                    ],
                ),
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 4
    # solvers are functions, so not simple to verify


def test_sample_id(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=FlowSpec(
            log_dir=init_test_logs(),
            tasks=[FlowTask(name=task_file + "@noop", sample_id=1)],
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert len(tasks_arg[0].dataset.samples) == 1
    assert tasks_arg[0].dataset.samples[0].id == 1


def test_all_tasks_in_file(mock_eval_set: MagicMock) -> None:
    file = task_dir + "/three_tasks.py"
    run_eval_set(
        spec=FlowSpec(
            log_dir=init_test_logs(),
            tasks=[file],
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 3
    assert tasks_arg[0].name == "noop1"
    assert tasks_arg[1].name == "noop2"
    assert tasks_arg[2].name == "noop3"


def test_config_generate_config(mock_eval_set: MagicMock) -> None:
    config_system_message = "Config System Message"
    task_system_message = "Task System Message"
    model_system_message = "Model System Message"
    config_temperature = 0.0
    task_temperature = 0.2
    config_max_tokens = 100

    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    config=GenerateConfig(
                        system_message=config_system_message,
                        temperature=config_temperature,
                        max_tokens=config_max_tokens,
                    ),
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
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
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)

    task_config = tasks_arg[0].config
    assert task_config.system_message == model_system_message
    assert task_config.temperature == task_temperature
    assert task_config.max_tokens == config_max_tokens

    model_config = tasks_arg[0].model.config
    assert model_config.system_message == model_system_message
    assert model_config.temperature is None
    assert model_config.max_tokens is None


def test_config_model_overrides(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    config=GenerateConfig(
                        system_message="Global Default",
                    ),
                    model=FlowModel(
                        config=GenerateConfig(system_message="Model Default")
                    ),
                    model_prefix={
                        "mockllm/": FlowModel(
                            config=GenerateConfig(system_message="Model Prefix Default")
                        )
                    },
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        config=GenerateConfig(
                            system_message="Task",
                        ),
                        model=FlowModel(
                            name="mockllm/mock-llm",
                            config=GenerateConfig(system_message="Model"),
                        ),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)

    task_config = tasks_arg[0].config
    assert task_config.system_message == "Model"

    model_config = tasks_arg[0].model.config
    assert model_config.system_message == "Model"


def test_config_model_prefix_default_overrides(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    config=GenerateConfig(
                        system_message="Global Default",
                    ),
                    model=FlowModel(
                        config=GenerateConfig(system_message="Model Default")
                    ),
                    model_prefix={
                        "mockllm/": FlowModel(
                            config=GenerateConfig(system_message="Model Prefix Default")
                        )
                    },
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        config=GenerateConfig(
                            system_message="Task",
                        ),
                        model=FlowModel(
                            name="mockllm/mock-llm",
                        ),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)

    task_config = tasks_arg[0].config
    assert task_config.system_message == "Model Prefix Default"

    model_config = tasks_arg[0].model.config
    assert model_config.system_message == "Model Prefix Default"


def test_config_model_default_overrides(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    config=GenerateConfig(
                        system_message="Global Default",
                    ),
                    model=FlowModel(
                        config=GenerateConfig(system_message="Model Default")
                    ),
                    model_prefix={
                        "NOMATCH/": FlowModel(
                            config=GenerateConfig(system_message="Model Prefix Default")
                        )
                    },
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        config=GenerateConfig(
                            system_message="Task",
                        ),
                        model=FlowModel(
                            name="mockllm/mock-llm",
                        ),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)

    task_config = tasks_arg[0].config
    assert task_config.system_message == "Model Default"

    model_config = tasks_arg[0].model.config
    assert model_config.system_message == "Model Default"


def test_config_model_prefixes(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    model_prefix={
                        "mockllm/": FlowModel(
                            config=GenerateConfig(
                                system_message="Model Provider Prefix Default"
                            )
                        ),
                        "mockllm/mock-": FlowModel(
                            config=GenerateConfig(
                                system_message="Model Class Prefix Default"
                            )
                        ),
                    },
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model=FlowModel(
                            name="mockllm/mock-llm",
                        ),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)

    task_config = tasks_arg[0].config
    assert task_config.system_message == "Model Class Prefix Default"

    model_config = tasks_arg[0].model.config
    assert model_config.system_message == "Model Class Prefix Default"


def test_task_defaults(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    task=FlowTask(model="mockllm/mock-llm"),
                    task_prefix={task_file: FlowTask(args={"subset": "original"})},
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@task_with_params",
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)
    assert tasks_arg[0].model.name == "mock-llm"
    assert tasks_arg[0].metadata["subset"] == "original"


def test_task_not_given(mock_eval_set: MagicMock) -> None:
    config = FlowSpec(
        log_dir=init_test_logs(),
        tasks=[
            FlowTask(
                name=task_file + "@task_with_params",
                metadata=not_given,
            )
        ],
    )
    dump = config_to_yaml(config)
    spec = FlowSpec.model_validate(yaml.safe_load(dump), extra="forbid")

    run_eval_set(
        spec=spec,
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert tasks_arg[0].metadata["subset"] == "original"

    mock_eval_set.reset_mock()

    config = FlowSpec(
        log_dir=init_test_logs(),
        tasks=[
            FlowTask(
                name=task_file + "@task_with_params",
                metadata=None,
            )
        ],
    )
    dump = config_to_yaml(config)
    spec = FlowSpec.model_validate(yaml.safe_load(dump), extra="forbid")

    run_eval_set(
        spec=spec,
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert tasks_arg[0].metadata is None


def test_solver_defaults(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    solver=FlowSolver(args={"template": "Default"}),
                    solver_prefix={
                        "inspect_ai": FlowSolver(args={"template": "Prefix"})
                    },
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model="mockllm/mock-llm",
                        solver="inspect_ai/system_message",
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].solver, Solver)


def test_agent_defaults(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                defaults=FlowDefaults(
                    agent=FlowAgent(args={"description": "Default Description"}),
                    solver_prefix={
                        "inspect_ai": FlowSolver(args={"prompt": "Prefix Prompt"})
                    },
                ),
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model="mockllm/mock-llm",
                        solver=FlowAgent(name="inspect_ai/react"),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].solver, Agent)
    # TODO:ransom this doesn't test the args - probably need to write an agent to do that


def test_dry_run(mock_eval_set: MagicMock) -> None:
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=init_test_logs(),
                tasks=[
                    FlowTask(
                        name=task_file + "@task_with_get_model",
                        model=FlowModel(name="mockllm/mock-llm"),
                    )
                ],
            )
        ),
        base_dir=".",
        dry_run=True,
    )

    mock_eval_set.assert_not_called()


def test_task_with_two_model_configs() -> None:
    # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
    # So can not use a mock
    log_dir = init_test_logs()

    config = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(
            task=[FlowTask(name=task_file + "@noop")],
            model=models_matrix(
                model="mockllm/mock-llm1",
                config=[
                    GenerateConfig(temperature=0),
                    GenerateConfig(temperature=0.5),
                ],
            ),
        ),
    )
    run_eval_set(spec=(config), base_dir=".")

    verify_test_logs(config, log_dir)


def test_task_with_two_solvers() -> None:
    # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
    # So can not use a mock
    log_dir = init_test_logs()

    config = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(
            task=FlowTask(name=task_file + "@noop", model="mockllm/mock-llm"),
            solver=[
                *solvers_matrix(
                    solver="inspect_ai/system_message",
                    args=[
                        {"template": "test system message"},
                        {"template": "another test system message"},
                    ],
                ),
                [
                    FlowSolver(
                        name="inspect_ai/system_message",
                        args={"template": "another test system message"},
                    ),
                    FlowSolver(name="inspect_ai/generate"),
                ],
            ],
        ),
    )
    run_eval_set(spec=(config), base_dir=".")

    verify_test_logs(config, log_dir)


def test_default_model_roles(mock_eval_set: MagicMock) -> None:
    default_model_roles = {"grader": "mockllm/default-grader"}
    task_model_roles = {"mark": "mockllm/mark"}
    log_dir = init_test_logs()
    config = FlowSpec(
        log_dir=log_dir,
        defaults=FlowDefaults(
            task=FlowTask(model_roles=default_model_roles),
        ),
        tasks=[
            task_file + "@noop",
            FlowTask(
                name=task_file + "@noop",
                model_roles=task_model_roles,
            ),
        ],
    )

    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert isinstance(tasks_arg[0], Task)
    assert tasks_arg[0].model_roles.keys() == default_model_roles.keys()
    assert tasks_arg[1].model_roles.keys() == task_model_roles.keys()


def test_logs_allow_dirty(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()

    config = FlowSpec(
        log_dir=log_dir,
        tasks=[
            task_file + "@noop",
        ],
    )

    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert call_args.kwargs["log_dir_allow_dirty"] is None

    mock_eval_set.reset_mock()

    config.options = FlowOptions(log_dir_allow_dirty=True)
    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert call_args.kwargs["log_dir_allow_dirty"] is True


def test_bundle_url_map(
    mock_eval_set: MagicMock, recording_console: Console, tmp_path: Path
) -> None:
    log_dir = init_test_logs()
    config = FlowSpec(
        log_dir=log_dir,
        options=FlowOptions(
            bundle_dir=str(tmp_path / "logs" / "bundle_test"),
            bundle_url_mappings={tmp_path.as_posix(): "http://example.com/bundle"},
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    out = recording_console.export_text()
    assert "Bundle: http://example.com/bundle" in out


def test_bundle_url_map_no_change(
    mock_eval_set: MagicMock, recording_console: Console
) -> None:
    path = Path.cwd().as_posix()
    config = FlowSpec(
        log_dir=init_test_logs(),
        options=FlowOptions(
            bundle_dir=path + "logs/bundle_test",
            bundle_url_mappings={"not_there": "http://example.com/bundle"},
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    out = recording_console.export_text()
    assert "Bundle:" in out


def test_217_bundle_error_message(tmp_path: Path) -> None:
    log_dir = init_test_logs()

    bundle_dir = str(tmp_path / "bundle_test")
    config = FlowSpec(
        log_dir=log_dir,
        options=FlowOptions(bundle_dir=bundle_dir),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )

    run_eval_set(spec=(config), base_dir=".")

    assert config.tasks
    config.tasks = list(config.tasks) + [
        FlowTask(name=task_file + "@noop", model="mockllm/mock-llm2")
    ]

    with pytest.raises(FlowHandledError) as e:
        run_eval_set(spec=(config), base_dir=".")
    assert e.value.__cause__
    assert isinstance(e.value.__cause__, PrerequisiteError)
    assert "'bundle_overwrite'" in str(e.value.__cause__.message)


def test_545_bundle_url_map_embed_viewer(
    mock_eval_set: MagicMock, recording_console: Console
) -> None:
    log_dir = init_test_logs()
    config = FlowSpec(
        log_dir=log_dir,
        options=FlowOptions(
            bundle_url_mappings={log_dir: "http://example.com/view"},
            embed_viewer=True,
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    out = recording_console.export_text()
    assert "Viewer: http://example.com/view/" in out


def test_bundle_url_and_embed_viewer(
    mock_eval_set: MagicMock, recording_console: Console, tmp_path: Path
) -> None:
    log_dir = init_test_logs()
    bundle_dir = str(tmp_path / "logs" / "bundle_test")

    config = FlowSpec(
        log_dir=log_dir,
        options=FlowOptions(
            bundle_dir=bundle_dir,
            bundle_url_mappings={
                tmp_path.as_posix(): "http://example.com/bundle",
                log_dir: "http://example.com/view",
            },
            embed_viewer=True,
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    out = recording_console.export_text()
    assert "Viewer: http://example.com/view/" in out
    assert "Bundle: http://example.com/bundle" in out


def test_prerequisite_error() -> None:
    log_dir = init_test_logs()

    config = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )

    run_eval_set(spec=(config), base_dir=".")

    config.options = FlowOptions(eval_set_id="different_id")

    with pytest.raises(FlowHandledError) as e:
        run_eval_set(spec=(config), base_dir=".")
    assert e.value.__cause__
    assert isinstance(e.value.__cause__, PrerequisiteError)
    assert (
        "The eval set ID 'different_id' is not the same as the existing eval set ID"
        in str(e.value.__cause__.message)
    )
    assert "overwrite" not in str(e.value.__cause__.message)


@solver
def fail_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        raise RuntimeError("Intentional Task Failure")

    return solve


def test_task_failure() -> None:
    log_dir = init_test_logs()

    spec = FlowSpec(
        log_dir=log_dir,
        options=FlowOptions(retry_attempts=0),
        tasks=[FlowTask(name=task_file + "@noop", solver="fail_solver")],
    )
    result = run_eval_set(spec=spec, base_dir=".")
    assert result[0] is False


def test_eval_set_args(mock_eval_set: MagicMock) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        options=FlowOptions(
            retry_attempts=7,
            retry_wait=0.5,
            retry_connections=0.75,
            retry_cleanup=True,
            sandbox=SandboxEnvironmentSpec("docker"),
            sandbox_cleanup=False,
            tags=["test", "test_project"],
            metadata={"project": "test_project"},
            trace=True,
            display="rich",
            approval=ApprovalPolicyConfig(
                approvers=[
                    ApproverPolicyConfig(
                        name="auto", tools="*", params={"decision": "approve"}
                    )
                ]
            ),
            score=False,
            log_level="debug",
            log_level_transcript="info",
            log_format="json",
            limit=50,
            sample_shuffle=1234,
            fail_on_error=0.1,
            continue_on_fail=True,
            retry_on_error=5,
            debug_errors=True,
            model_cost_config="mock_cost_config",
            max_samples=20,
            max_tasks=15,
            max_subprocesses=400,
            max_sandboxes=2,
            log_samples=False,
            log_realtime=False,
            log_images=True,
            log_model_api=True,
            log_refusals=True,
            log_buffer=2048,
            log_shared=15,
            bundle_dir="logs/bundle_test",
            bundle_overwrite=True,
            log_dir_allow_dirty=True,
            eval_set_id="test_eval_set_001",
            embed_viewer=True,
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    run_eval_set(spec=spec, base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert spec.options
    assert call_args.kwargs["retry_attempts"] == spec.options.retry_attempts
    assert call_args.kwargs["retry_wait"] == spec.options.retry_wait
    assert call_args.kwargs["retry_connections"] == spec.options.retry_connections
    assert call_args.kwargs["retry_cleanup"] == spec.options.retry_cleanup
    assert call_args.kwargs["sandbox"] == spec.options.sandbox
    assert call_args.kwargs["sandbox_cleanup"] == spec.options.sandbox_cleanup
    assert call_args.kwargs["tags"] == spec.options.tags
    assert call_args.kwargs["metadata"] == spec.options.metadata
    assert call_args.kwargs["trace"] == spec.options.trace
    assert call_args.kwargs["display"] == spec.options.display
    assert call_args.kwargs["approval"] == spec.options.approval
    assert call_args.kwargs["score"] == spec.options.score
    assert call_args.kwargs["log_level"] == spec.options.log_level
    assert call_args.kwargs["log_level_transcript"] == spec.options.log_level_transcript
    assert call_args.kwargs["log_format"] == spec.options.log_format
    assert call_args.kwargs["limit"] == spec.options.limit
    assert call_args.kwargs["sample_shuffle"] == spec.options.sample_shuffle
    assert call_args.kwargs["fail_on_error"] == spec.options.fail_on_error
    assert call_args.kwargs["continue_on_fail"] == spec.options.continue_on_fail
    assert call_args.kwargs["retry_on_error"] == spec.options.retry_on_error
    assert call_args.kwargs["debug_errors"] == spec.options.debug_errors
    assert call_args.kwargs["model_cost_config"] == spec.options.model_cost_config
    assert call_args.kwargs["max_samples"] == spec.options.max_samples
    assert call_args.kwargs["max_tasks"] == spec.options.max_tasks
    assert call_args.kwargs["max_subprocesses"] == spec.options.max_subprocesses
    assert call_args.kwargs["max_sandboxes"] == spec.options.max_sandboxes
    assert call_args.kwargs["log_samples"] == spec.options.log_samples
    assert call_args.kwargs["log_realtime"] == spec.options.log_realtime
    assert call_args.kwargs["log_images"] == spec.options.log_images
    assert call_args.kwargs["log_model_api"] == spec.options.log_model_api
    assert call_args.kwargs["log_refusals"] == spec.options.log_refusals
    assert call_args.kwargs["log_buffer"] == spec.options.log_buffer
    assert call_args.kwargs["log_shared"] == spec.options.log_shared
    assert call_args.kwargs["bundle_dir"] == spec.options.bundle_dir
    assert call_args.kwargs["bundle_overwrite"] == spec.options.bundle_overwrite
    assert call_args.kwargs["log_dir_allow_dirty"] == spec.options.log_dir_allow_dirty
    assert call_args.kwargs["eval_set_id"] == spec.options.eval_set_id
    assert call_args.kwargs["embed_viewer"] == spec.options.embed_viewer


@pytest.mark.asyncio
async def test_task_with_scorer(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=log_dir,
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model=FlowModel(name="mockllm/mock-llm"),
                        scorer=FlowScorer(
                            name="inspect_ai/answer", args={"pattern": "letter"}
                        ),
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    assert isinstance(tasks_arg[0], Task)
    assert isinstance(tasks_arg[0].model, Model)
    state = TaskState(
        model=ModelName("mockllm/mock-llm"),
        sample_id=1,
        epoch=1,
        input="Question: What is the answer?\n",
        messages=[],
        output=ModelOutput(completion="ANSWER: b"),
    )
    scorer = tasks_arg[0].scorer[0]
    score = await scorer(state, target="b")
    assert score.value == "C"


@pytest.mark.asyncio
async def test_task_with_scorer_list(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    run_eval_set(
        spec=(
            FlowSpec(
                log_dir=log_dir,
                tasks=[
                    FlowTask(
                        name=task_file + "@noop",
                        model=FlowModel(name="mockllm/mock-llm"),
                        scorer=[
                            FlowScorer(
                                name="inspect_ai/answer", args={"pattern": "letter"}
                            ),
                            "inspect_ai/choice",
                        ],
                    )
                ],
            )
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 1
    scorers = tasks_arg[0].scorer
    assert len(scorers) == 2


def test_no_log_dir() -> None:
    spec = FlowSpec(
        log_dir="",
        tasks=[
            task_file + "@noop",
        ],
    )

    with pytest.raises(ValueError) as e:
        run_eval_set(spec=spec, base_dir=".")
    assert "log_dir must be set" in str(e.value)


def test_duplicate_task_identifier() -> None:
    log_dir = init_test_logs()

    spec = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(
            task=[task_file + "@noop"], model=["mockllm/model1", "mockllm/model1"]
        ),
    )
    with pytest.raises(ValueError) as e:
        run_eval_set(spec=spec, base_dir=".")
    assert e.value.args[0].startswith("Duplicate task found:")


def test_log_copy(recording_console: Console) -> None:
    log_dir = init_test_logs()
    store_dir = init_test_store()

    spec = FlowSpec(
        log_dir=log_dir,
        store=FlowStoreConfig(path=store_dir, read=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")

    verify_test_logs(spec, log_dir)

    recording_console.export_text()  # Clear previous output

    log_dir2 = log_dir + "_2"
    if Path(log_dir2).exists():
        shutil.rmtree(log_dir2)
    spec.log_dir = log_dir2

    run_eval_set(spec=spec, base_dir=".")
    verify_test_logs(spec, log_dir2)

    out = recording_console.export_text()
    assert "Found 1 existing log in store. Copying to log directory" in out


def test_log_copy_store_read_off_by_default(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs1")
    store_dir = init_test_store()

    # Run a real eval to index the log in the store
    spec = FlowSpec(
        log_dir=log_dir,
        store=FlowStoreConfig(path=store_dir, read=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")

    # Second run with a new log_dir and store read off (default)
    log_dir2 = str(tmp_path / "logs2")
    spec.log_dir = log_dir2
    spec.store = FlowStoreConfig(path=store_dir)  # read=False by default

    with patch("inspect_flow._runner.run.eval_set") as mock:
        mock.return_value = (True, [])
        run_eval_set(spec=spec, base_dir=".")

    # No logs should have been copied from the store
    assert not list(Path(log_dir2).glob("*.eval"))


def test_store_write_off_no_using_store_message(recording_console: Console) -> None:
    log_dir = init_test_logs()
    store_dir = init_test_store()

    spec = FlowSpec(
        log_dir=log_dir,
        store=FlowStoreConfig(path=store_dir, write=False),  # read=False by default
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")

    assert "Using store" not in recording_console.export_text()


def test_store_none_write_explicit_warns(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        store=FlowStoreConfig(path=None, write=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    assert "store_write has no effect" in recording_console.export_text()


def test_store_none_write_default_no_warn(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        store=FlowStoreConfig(path=None),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    assert "store_write has no effect" not in recording_console.export_text()


def test_store_none_read_warns(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        store=FlowStoreConfig(path=None, read=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    assert "store_read has no effect" in recording_console.export_text()


def test_using_store_write_only(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        store=FlowStoreConfig(path=init_test_store()),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    assert "Using store (write only):" in recording_console.export_text()


def test_using_store_read_write(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        store=FlowStoreConfig(path=init_test_store(), read=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    assert "Using store (read-write):" in recording_console.export_text()


def test_using_store_read_only(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        store=FlowStoreConfig(path=init_test_store(), read=True, write=False),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    assert "Using store (read only):" in recording_console.export_text()


def test_log_copy_local_and_store(recording_console: Console, tmp_path: Path) -> None:
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    task1 = FlowTask(name=task_file + "@noop", model="mockllm/model-a")
    task2 = FlowTask(name=task_file + "@noop", model="mockllm/model-b")

    # Run task1 in logdir1 (store indexes it automatically)
    run_eval_set(spec=FlowSpec(log_dir=log_dir1, tasks=[task1]), base_dir=".")
    # Run task2 in logdir2 (store indexes it automatically)
    run_eval_set(spec=FlowSpec(log_dir=log_dir2, tasks=[task2]), base_dir=".")

    recording_console.export_text()  # Clear previous output

    # Run both tasks in logdir1 — task1 found locally, task2 copied from store
    run_eval_set(
        spec=FlowSpec(
            log_dir=log_dir1, store=FlowStoreConfig(read=True), tasks=[task1, task2]
        ),
        base_dir=".",
    )

    out = recording_console.export_text()
    assert "Found 1 existing log in log directory" in out
    assert "Found 1 existing log in store. Copying to log directory" in out


def test_store_log_gone(recording_console: Console) -> None:
    log_handler: LogHandlerVar = {"handler": None}
    init_flow_logging(log_level="info", log_handler_var=log_handler)
    if log_handler["handler"]:
        log_handler["handler"].console = recording_console

    log_dir = init_test_logs()
    store_dir = init_test_store()

    spec = FlowSpec(
        log_dir=log_dir,
        store=FlowStoreConfig(path=store_dir, read=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")

    verify_test_logs(spec, log_dir)

    log_dir = init_test_logs()
    recording_console.export_text()  # Clear previous output

    run_eval_set(spec=spec, base_dir=".")
    out = recording_console.export_text()
    assert "Failed to read log" in out


def test_log_copy_s3(recording_console: Console, mock_s3: BaseClient) -> None:
    log_dir = "s3://test-bucket/logs"
    store_dir = init_test_store()

    spec = FlowSpec(
        log_dir=log_dir,
        store=FlowStoreConfig(path=store_dir, read=True),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec, base_dir=".")
    verify_test_logs(spec, log_dir)

    recording_console.export_text()  # Clear previous output

    log_dir2 = log_dir + "_2"
    spec.log_dir = log_dir2

    with patch("inspect_flow._runner.run.eval_set") as mock:
        mock.return_value = (True, [])
        run_eval_set(spec=spec, base_dir=".")
    verify_test_logs(spec, log_dir2)

    out = recording_console.export_text()
    assert "Found 1 existing log in store. Copying to log directory" in out


def test_log_level_from_flow(mock_eval_set: MagicMock) -> None:
    init_flow_logging(log_level="info")
    run_eval_set(
        spec=FlowSpec(
            log_dir=init_test_logs(),
            tasks=[task_file + "@noop"],
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    assert mock_eval_set.call_args.kwargs["log_level"] == "info"


def test_log_level_from_options(mock_eval_set: MagicMock) -> None:
    init_flow_logging(log_level="info")
    run_eval_set(
        spec=FlowSpec(
            log_dir=init_test_logs(),
            options=FlowOptions(log_level="debug"),
            tasks=[task_file + "@noop"],
        ),
        base_dir=".",
    )

    mock_eval_set.assert_called_once()
    assert mock_eval_set.call_args.kwargs["log_level"] == "debug"


def test_eval_set_error(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(task=[task_file + "@noop"], model=["mockllm/model1"]),
    )
    mock_eval_set.side_effect = ValueError("Test error from eval_set")

    with pytest.raises(FlowHandledError) as e:
        run_eval_set(spec=spec, base_dir=".")

    assert e.value.__cause__ is not None
    assert isinstance(e.value.__cause__, ValueError)
    assert "Test error from eval_set" in str(e.value.__cause__)


def test_eval_set_keyboard_interrupt(
    mock_eval_set: MagicMock, recording_console: Console
) -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(task=[task_file + "@noop"], model=["mockllm/model1"]),
    )
    mock_eval_set.side_effect = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        run_eval_set(spec=spec, base_dir=".")

    out = recording_console.export_text()
    assert "Eval Set Failed with Exception" in out
