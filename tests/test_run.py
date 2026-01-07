import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from inspect_ai import Task
from inspect_ai._util.error import PrerequisiteError
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
    FlowTask,
    models_matrix,
    solvers_matrix,
    tasks_matrix,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.run import _run_eval_set
from inspect_flow._types.flow_types import FlowScorer, not_given

from .test_helpers.log_helpers import init_test_db, init_test_logs, verify_test_logs

task_dir = (Path(__file__).parent / "local_eval" / "src" / "local_eval").resolve()
task_file = str(task_dir / "noop.py")


def test_task_with_get_model() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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

    config = FlowSpec(
        log_dir=log_dir,
        tasks=tasks_matrix(
            task=task_file + "@noop",
            model=[
                FlowModel(name="mockllm/mock-llm1"),
                FlowModel(name="mockllm/mock-llm2"),
            ],
        ),
    )
    _run_eval_set(spec=(config), base_dir=".")

    verify_test_logs(config, log_dir)


def test_model_generate_config() -> None:
    system_message = "Test System Message"
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_default_model_config() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
                    tasks=[FlowTask(name=task_file + "@noop")],
                )
            ),
            base_dir=".",
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert tasks_arg[0].model is None


def test_task_model() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_write_config() -> None:
    log_dir = init_test_logs()

    spec = FlowSpec(
        cache=None,
        log_dir=log_dir,
        tasks=[
            FlowTask(
                name=task_file + "@noop",
                model=FlowModel(name="mockllm/mock-llm"),
            )
        ],
    )
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=spec, base_dir=".")

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


def test_matrix_args() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_matrix_model_roles() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
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
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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
        assert (
            tasks_arg[1].model_roles["conartist"].config.system_message
            == system_message
        )


def test_matrix_solvers() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_sample_id() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=FlowSpec(
                log_dir="logs/flow_test",
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


def test_all_tasks_in_file() -> None:
    file = str(task_dir / "three_tasks.py")
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=FlowSpec(
                log_dir="logs/flow_test",
                tasks=[file],
            ),
            base_dir=".",
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 3
        assert tasks_arg[0].name == file + "@noop1"
        assert tasks_arg[1].name == file + "@noop2"
        assert tasks_arg[2].name == file + "@noop3"


def test_config_generate_config() -> None:
    config_system_message = "Config System Message"
    task_system_message = "Task System Message"
    model_system_message = "Model System Message"
    config_temperature = 0.0
    task_temperature = 0.2
    config_max_tokens = 100

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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
                                config=GenerateConfig(
                                    system_message=model_system_message
                                ),
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


def test_config_model_overrides() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=GenerateConfig(
                            system_message="Global Default",
                        ),
                        model=FlowModel(
                            config=GenerateConfig(system_message="Model Default")
                        ),
                        model_prefix={
                            "mockllm/": FlowModel(
                                config=GenerateConfig(
                                    system_message="Model Prefix Default"
                                )
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


def test_config_model_prefix_default_overrides() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=GenerateConfig(
                            system_message="Global Default",
                        ),
                        model=FlowModel(
                            config=GenerateConfig(system_message="Model Default")
                        ),
                        model_prefix={
                            "mockllm/": FlowModel(
                                config=GenerateConfig(
                                    system_message="Model Prefix Default"
                                )
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


def test_config_model_default_overrides() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=GenerateConfig(
                            system_message="Global Default",
                        ),
                        model=FlowModel(
                            config=GenerateConfig(system_message="Model Default")
                        ),
                        model_prefix={
                            "NOMATCH/": FlowModel(
                                config=GenerateConfig(
                                    system_message="Model Prefix Default"
                                )
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


def test_config_model_prefixes() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_task_defaults() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_task_not_given() -> None:
    config = FlowSpec(
        log_dir="logs/flow_test",
        tasks=[
            FlowTask(
                name=task_file + "@task_with_params",
                metadata=not_given,
            )
        ],
    )
    dump = config_to_yaml(config)
    spec = FlowSpec.model_validate(yaml.safe_load(dump), extra="forbid")

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=spec,
            base_dir=".",
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert tasks_arg[0].metadata["subset"] == "original"

    config = FlowSpec(
        log_dir="logs/flow_test",
        tasks=[
            FlowTask(
                name=task_file + "@task_with_params",
                metadata=None,
            )
        ],
    )
    dump = config_to_yaml(config)
    spec = FlowSpec.model_validate(yaml.safe_load(dump), extra="forbid")

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=spec,
            base_dir=".",
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert tasks_arg[0].metadata is None


def test_solver_defaults() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_agent_defaults() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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


def test_dry_run():
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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
    _run_eval_set(spec=(config), base_dir=".")

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
    _run_eval_set(spec=(config), base_dir=".")

    verify_test_logs(config, log_dir)


def test_default_model_roles() -> None:
    default_model_roles = {"grader": "mockllm/default-grader"}
    task_model_roles = {"mark": "mockllm/mark"}
    config = FlowSpec(
        log_dir="logs/flow_test",
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

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert isinstance(tasks_arg[0], Task)
    assert tasks_arg[0].model_roles.keys() == default_model_roles.keys()
    assert tasks_arg[1].model_roles.keys() == task_model_roles.keys()


def test_logs_allow_dirty() -> None:
    config = FlowSpec(
        log_dir="logs/flow_test",
        tasks=[
            task_file + "@noop",
        ],
    )

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert call_args.kwargs["log_dir_allow_dirty"] is None

    config.options = FlowOptions(log_dir_allow_dirty=True)
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert call_args.kwargs["log_dir_allow_dirty"] is True


def test_bundle_url_map(capsys) -> None:
    path = Path.cwd().as_posix()
    config = FlowSpec(
        log_dir="logs/flow_test",
        options=FlowOptions(
            bundle_dir=path + "logs/bundle_test",
            bundle_url_mappings={path: "http://example.com/bundle"},
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    captured = capsys.readouterr()
    assert "Bundle URL: http://example.com/bundle" in captured.out


def test_bundle_url_map_no_change(capsys) -> None:
    path = Path.cwd().as_posix()
    config = FlowSpec(
        log_dir="logs/flow_test",
        options=FlowOptions(
            bundle_dir=path + "logs/bundle_test",
            bundle_url_mappings={"not_there": "http://example.com/bundle"},
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=(config), base_dir=".")

    mock_eval_set.assert_called_once()
    captured = capsys.readouterr()
    assert "Bundle URL:" not in captured.out


def test_217_bundle_error_message() -> None:
    log_dir = init_test_logs()

    bundle_dir = log_dir + "/bundle_test"
    config = FlowSpec(
        log_dir=log_dir,
        options=FlowOptions(bundle_dir=bundle_dir),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )

    _run_eval_set(spec=(config), base_dir=".")

    assert config.tasks
    config.tasks = list(config.tasks) + [
        FlowTask(name=task_file + "@noop", model="mockllm/mock-llm2")
    ]

    with pytest.raises(PrerequisiteError) as e:
        _run_eval_set(spec=(config), base_dir=".")
    assert "'bundle_overwrite'" in str(e)
    assert "'bundle_overwrite'" in str(e.value.message)


def test_prerequisite_error() -> None:
    log_dir = init_test_logs()

    config = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )

    _run_eval_set(spec=(config), base_dir=".")

    config.options = FlowOptions(eval_set_id="different_id")

    with pytest.raises(PrerequisiteError) as e:
        _run_eval_set(spec=(config), base_dir=".")
    assert (
        "The eval set ID 'different_id' is not the same as the existing eval set ID"
        in str(e.value.message)
    )
    assert "overwrite" not in str(e.value.message)


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
    result = _run_eval_set(spec=spec, base_dir=".")
    assert result[0] is False


def test_eval_set_args() -> None:
    spec = FlowSpec(
        log_dir="logs/flow_test",
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
            max_samples=20,
            max_tasks=15,
            max_subprocesses=400,
            max_sandboxes=2,
            log_samples=False,
            log_realtime=False,
            log_images=True,
            log_buffer=2048,
            log_shared=15,
            bundle_dir="logs/bundle_test",
            bundle_overwrite=True,
            log_dir_allow_dirty=True,
            eval_set_id="test_eval_set_001",
        ),
        tasks=[
            task_file + "@noop",
        ],
    )

    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(spec=spec, base_dir=".")

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
    assert call_args.kwargs["max_samples"] == spec.options.max_samples
    assert call_args.kwargs["max_tasks"] == spec.options.max_tasks
    assert call_args.kwargs["max_subprocesses"] == spec.options.max_subprocesses
    assert call_args.kwargs["max_sandboxes"] == spec.options.max_sandboxes
    assert call_args.kwargs["log_samples"] == spec.options.log_samples
    assert call_args.kwargs["log_realtime"] == spec.options.log_realtime
    assert call_args.kwargs["log_images"] == spec.options.log_images
    assert call_args.kwargs["log_buffer"] == spec.options.log_buffer
    assert call_args.kwargs["log_shared"] == spec.options.log_shared
    assert call_args.kwargs["bundle_dir"] == spec.options.bundle_dir
    assert call_args.kwargs["bundle_overwrite"] == spec.options.bundle_overwrite
    assert call_args.kwargs["log_dir_allow_dirty"] == spec.options.log_dir_allow_dirty
    assert call_args.kwargs["eval_set_id"] == spec.options.eval_set_id


@pytest.mark.asyncio
async def test_task_with_scorer() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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
async def test_task_with_scorer_list() -> None:
    with patch("inspect_flow._runner.run.eval_set") as mock_eval_set:
        _run_eval_set(
            spec=(
                FlowSpec(
                    log_dir="logs/flow_test",
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
        _run_eval_set(spec=spec, base_dir=".")
    assert "log_dir must be set" in str(e.value)


def test_duplicate_task_identifier() -> None:
    spec = FlowSpec(
        log_dir="logs/flow_test",
        tasks=tasks_matrix(
            task=[task_file + "@noop"], model=["mockllm/model1", "mockllm/model1"]
        ),
    )
    with pytest.raises(ValueError) as e:
        _run_eval_set(spec=spec, base_dir=".")
    assert e.value.args[0].startswith("Duplicate task found:")


def test_log_copy(capsys) -> None:
    log_dir = init_test_logs()
    db_dir = init_test_db()

    spec = FlowSpec(
        log_dir=log_dir,
        cache=db_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    _run_eval_set(spec=spec, base_dir=".")

    verify_test_logs(spec, log_dir)

    capsys.readouterr()  # Clear previous output

    log_dir2 = Path(log_dir + "_2")
    if log_dir2.exists():
        shutil.rmtree(log_dir2)
    spec.log_dir = str(log_dir2)

    _run_eval_set(spec=spec, base_dir=".")
    verify_test_logs(spec, log_dir)

    out = capsys.readouterr().out
    assert "Copying existing log file" in out


def test_store_log_gone(capsys) -> None:
    log_dir = init_test_logs()
    db_dir = init_test_db()

    spec = FlowSpec(
        log_dir=log_dir,
        cache=db_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    _run_eval_set(spec=spec, base_dir=".")

    verify_test_logs(spec, log_dir)

    log_dir = init_test_logs()
    capsys.readouterr()  # Clear previous output

    with pytest.raises(FileNotFoundError):
        _run_eval_set(spec=spec, base_dir=".")
    out = capsys.readouterr().out
    assert "Failed to read log" in out
    assert "If expected, use 'flow store remove' to update the store." in out
