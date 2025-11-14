from pathlib import Path
from unittest.mock import patch

from inspect_ai import Task
from inspect_ai.agent import Agent
from inspect_ai.model import GenerateConfig, Model
from inspect_ai.solver import Solver
from inspect_flow import models_matrix, solvers_matrix, tasks_matrix
from inspect_flow._runner.run import _run_eval_set
from inspect_flow.types import (
    FlowAgent,
    FlowConfig,
    FlowDefaults,
    FlowGenerateConfig,
    FlowModel,
    FlowOptions,
    FlowSolver,
    FlowTask,
)

from .test_helpers.log_helpers import init_test_logs, verify_test_logs

task_dir = (
    Path(__file__).parent / "config" / "local_eval" / "src" / "local_eval"
).resolve()
task_file = str(task_dir / "noop.py")


def test_task_with_get_model() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=[
                        FlowTask(
                            name=task_file + "@task_with_get_model",
                            model=FlowModel(name="mockllm/mock-llm"),
                        )
                    ],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)


def test_task_with_two_models() -> None:
    # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
    # So can not use a mock
    log_dir = init_test_logs()

    config = FlowConfig(
        flow_dir=log_dir,
        tasks=tasks_matrix(
            task=task_file + "@noop",
            model=[
                FlowModel(name="mockllm/mock-llm1"),
                FlowModel(name="mockllm/mock-llm2"),
            ],
        ),
    )
    _run_eval_set(config=(config))

    verify_test_logs(config, log_dir)


def test_model_generate_config() -> None:
    system_message = "Test System Message"
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=[
                        FlowTask(
                            name=task_file + "@noop",
                            model=FlowModel(
                                name="mockllm/mock-llm",
                                config=FlowGenerateConfig(
                                    system_message=system_message
                                ),
                            ),
                        )
                    ],
                )
            )
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
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=[FlowTask(name=task_file + "@noop")],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert tasks_arg[0].model is None


def test_task_model() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=[
                        FlowTask(
                            name=task_file + "@noop",
                            model=FlowModel(name="mockllm/mock-llm"),
                        )
                    ],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)
        assert tasks_arg[0].model.name == "mock-llm"


def test_matrix_args() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=tasks_matrix(
                        task=FlowTask(
                            name=task_file + "@task_with_params",
                            model=FlowModel(name="mockllm/mock-llm"),
                        ),
                        args=[{"subset": "original"}, {"subset": "contrast"}],
                    ),
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert tasks_arg[0].metadata["subset"] == "original"
        assert tasks_arg[1].metadata["subset"] == "contrast"


def test_matrix_model_roles() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        system_message = "mock system message"
        model_roles1 = {
            "mark": "mockllm/mock-mark1",
            "conartist": "mockllm/mock-conartist1",
        }
        model_roles2 = {
            "mark": "mockllm/mock-mark2",
            "conartist": FlowModel(
                name="mockllm/mock-conartist2",
                config=FlowGenerateConfig(system_message=system_message),
            ),
        }
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=tasks_matrix(
                        task=FlowTask(
                            name=task_file + "@task_with_model_roles",
                            model=FlowModel(name="mockllm/mock-llm"),
                        ),
                        model_roles=[model_roles1, model_roles2],
                    ),
                )
            )
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
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
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
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 4
        # solvers are functions, so not simple to verify


def test_sample_id() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=[FlowTask(name=task_file + "@noop", sample_id=1)],
                )
            )
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
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=FlowConfig(
                flow_dir="logs/flow_test",
                tasks=[file],
            ),
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

    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=FlowGenerateConfig(
                            system_message=config_system_message,
                            temperature=config_temperature,
                            max_tokens=config_max_tokens,
                        ),
                    ),
                    tasks=[
                        FlowTask(
                            name=task_file + "@noop",
                            config=FlowGenerateConfig(
                                system_message=task_system_message,
                                temperature=task_temperature,
                            ),
                            model=FlowModel(
                                name="mockllm/mock-llm",
                                config=FlowGenerateConfig(
                                    system_message=model_system_message
                                ),
                            ),
                        )
                    ],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)

        task_config: GenerateConfig = tasks_arg[0].config
        assert task_config.system_message == model_system_message
        assert task_config.temperature == task_temperature
        assert task_config.max_tokens == config_max_tokens

        model_config: GenerateConfig = tasks_arg[0].model.config
        assert model_config.system_message == model_system_message
        assert model_config.temperature is None
        assert model_config.max_tokens is None


def test_config_model_overrides() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=FlowGenerateConfig(
                            system_message="Global Default",
                        ),
                        model=FlowModel(
                            config=FlowGenerateConfig(system_message="Model Default")
                        ),
                        model_prefix={
                            "mockllm/": FlowModel(
                                config=FlowGenerateConfig(
                                    system_message="Model Prefix Default"
                                )
                            )
                        },
                    ),
                    tasks=[
                        FlowTask(
                            name=task_file + "@noop",
                            config=FlowGenerateConfig(
                                system_message="Task",
                            ),
                            model=FlowModel(
                                name="mockllm/mock-llm",
                                config=FlowGenerateConfig(system_message="Model"),
                            ),
                        )
                    ],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)

        task_config: GenerateConfig = tasks_arg[0].config
        assert task_config.system_message == "Model"

        model_config: GenerateConfig = tasks_arg[0].model.config
        assert model_config.system_message == "Model"


def test_config_model_prefix_default_overrides() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=FlowGenerateConfig(
                            system_message="Global Default",
                        ),
                        model=FlowModel(
                            config=FlowGenerateConfig(system_message="Model Default")
                        ),
                        model_prefix={
                            "mockllm/": FlowModel(
                                config=FlowGenerateConfig(
                                    system_message="Model Prefix Default"
                                )
                            )
                        },
                    ),
                    tasks=[
                        FlowTask(
                            name=task_file + "@noop",
                            config=FlowGenerateConfig(
                                system_message="Task",
                            ),
                            model=FlowModel(
                                name="mockllm/mock-llm",
                            ),
                        )
                    ],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)

        task_config: GenerateConfig = tasks_arg[0].config
        assert task_config.system_message == "Model Prefix Default"

        model_config: GenerateConfig = tasks_arg[0].model.config
        assert model_config.system_message == "Model Prefix Default"


def test_config_model_default_overrides() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        config=FlowGenerateConfig(
                            system_message="Global Default",
                        ),
                        model=FlowModel(
                            config=FlowGenerateConfig(system_message="Model Default")
                        ),
                        model_prefix={
                            "NOMATCH/": FlowModel(
                                config=FlowGenerateConfig(
                                    system_message="Model Prefix Default"
                                )
                            )
                        },
                    ),
                    tasks=[
                        FlowTask(
                            name=task_file + "@noop",
                            config=FlowGenerateConfig(
                                system_message="Task",
                            ),
                            model=FlowModel(
                                name="mockllm/mock-llm",
                            ),
                        )
                    ],
                )
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)

        task_config: GenerateConfig = tasks_arg[0].config
        assert task_config.system_message == "Model Default"

        model_config: GenerateConfig = tasks_arg[0].model.config
        assert model_config.system_message == "Model Default"


def test_config_model_prefixes() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    defaults=FlowDefaults(
                        model_prefix={
                            "mockllm/": FlowModel(
                                config=FlowGenerateConfig(
                                    system_message="Model Provider Prefix Default"
                                )
                            ),
                            "mockllm/mock-": FlowModel(
                                config=FlowGenerateConfig(
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
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)

        task_config: GenerateConfig = tasks_arg[0].config
        assert task_config.system_message == "Model Class Prefix Default"

        model_config: GenerateConfig = tasks_arg[0].model.config
        assert model_config.system_message == "Model Class Prefix Default"


def test_task_defaults() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
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
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)
        assert tasks_arg[0].model.name == "mock-llm"
        assert tasks_arg[0].metadata["subset"] == "original"


def test_solver_defaults() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
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
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].solver, Solver)


def test_agent_defaults() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
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
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].solver, Agent)
        # TODO:ransom this doesn't test the args - probably need to write an agent to do that


def test_dry_run():
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(
            config=(
                FlowConfig(
                    flow_dir="logs/flow_test",
                    tasks=[
                        FlowTask(
                            name=task_file + "@task_with_get_model",
                            model=FlowModel(name="mockllm/mock-llm"),
                        )
                    ],
                )
            ),
            dry_run=True,
        )

    mock_eval_set.assert_not_called()


def test_task_with_two_model_configs() -> None:
    # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
    # So can not use a mock
    log_dir = init_test_logs()

    config = FlowConfig(
        flow_dir=log_dir,
        tasks=tasks_matrix(
            task=[FlowTask(name=task_file + "@noop")],
            model=models_matrix(
                model="mockllm/mock-llm1",
                config=[
                    FlowGenerateConfig(temperature=0),
                    FlowGenerateConfig(temperature=0.5),
                ],
            ),
        ),
    )
    _run_eval_set(config=(config))

    verify_test_logs(config, log_dir)


def test_task_with_two_solvers() -> None:
    # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
    # So can not use a mock
    log_dir = init_test_logs()

    config = FlowConfig(
        flow_dir=log_dir,
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
    _run_eval_set(config=(config))

    verify_test_logs(config, log_dir)


def test_default_model_roles() -> None:
    default_model_roles = {"grader": "mockllm/default-grader"}
    task_model_roles = {"mark": "mockllm/mark"}
    config = FlowConfig(
        flow_dir="logs/flow_test",
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

    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(config=(config))

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert isinstance(tasks_arg[0], Task)
    assert tasks_arg[0].model_roles.keys() == default_model_roles.keys()
    assert tasks_arg[1].model_roles.keys() == task_model_roles.keys()


def test_logs_allow_dirty() -> None:
    config = FlowConfig(
        flow_dir="logs/flow_test",
        tasks=[
            task_file + "@noop",
        ],
    )

    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(config=(config))

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert call_args.kwargs["log_dir_allow_dirty"] is True

    config.options = FlowOptions(log_dir_allow_dirty=False)
    with patch("inspect_ai.eval_set") as mock_eval_set:
        _run_eval_set(config=(config))

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert call_args.kwargs["log_dir_allow_dirty"] is False
