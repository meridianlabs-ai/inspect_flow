from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai import Task
from inspect_ai.model import GenerateConfig, Model
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.types import (
    AgentConfig,
    FlowConfig,
    FlowOptions,
    Matrix,
    ModelConfig,
    SolverConfig,
    TaskConfig,
)

from .test_helpers.log_helpers import init_test_logs, verify_test_logs

task_file = (
    Path(__file__).parents[1]
    / "examples"
    / "local_eval"
    / "src"
    / "local_eval"
    / "noop.py"
)


def test_task_with_get_model() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="task_with_get_model",
                                file=str(task_file.absolute()),
                            )
                        ],
                    )
                ],
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
        options=FlowOptions(log_dir=log_dir),
        matrix=[
            Matrix(
                models=[
                    ModelConfig(name="mockllm/mock-llm1"),
                    ModelConfig(name="mockllm/mock-llm2"),
                ],
                tasks=[TaskConfig(name="noop", file=str(task_file.absolute()))],
            ),
        ],
    )
    run_eval_set(config=config)

    verify_test_logs(config, log_dir)


def test_model_generate_config() -> None:
    system_message = "Test System Message"
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[
                            ModelConfig(
                                name="mockllm/mock-llm",
                                config=[GenerateConfig(system_message=system_message)],
                            ),
                        ],
                        tasks=[TaskConfig(name="noop", file=str(task_file.absolute()))],
                    ),
                ],
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
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        tasks=[TaskConfig(name="noop", file=str(task_file.absolute()))],
                    ),
                ],
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
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                                models=[ModelConfig(name="mockllm/mock-llm")],
                            )
                        ],
                    ),
                ],
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert isinstance(tasks_arg[0].model, Model)
        # TODO:ransom name has different meanings
        assert tasks_arg[0].model.name == "mock-llm"


def test_multiple_model_error() -> None:
    with pytest.raises(
        ValueError, match="Only one of matrix and task may specify model"
    ):
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                                models=[ModelConfig(name="mockllm/mock-llm2")],
                            )
                        ],
                    ),
                ],
            )
        )


def test_matrix_args() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        args=[{"subset": "original"}, {"subset": "contrast"}],
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="task_with_params", file=str(task_file.absolute())
                            )
                        ],
                    ),
                ],
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert tasks_arg[0].metadata["subset"] == "original"
        assert tasks_arg[1].metadata["subset"] == "contrast"


def test_task_args() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="task_with_params",
                                file=str(task_file.absolute()),
                                args=[{"subset": "original"}, {"subset": "contrast"}],
                            )
                        ],
                    ),
                ],
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert tasks_arg[0].metadata["subset"] == "original"
        assert tasks_arg[1].metadata["subset"] == "contrast"


def test_multiple_args_error() -> None:
    with pytest.raises(
        ValueError, match="Only one of matrix and task may specify args"
    ):
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        args=[{"subset": "original"}, {"subset": "contrast"}],
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                            ),
                            TaskConfig(
                                name="task_with_params",
                                file=str(task_file.absolute()),
                                args=[{"subset": "original"}, {"subset": "contrast"}],
                            ),
                        ],
                    ),
                ],
            )
        )


def test_two_matrix() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                            )
                        ],
                    ),
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="noop2",
                                file=str(task_file.absolute()),
                            )
                        ],
                    ),
                ],
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert tasks_arg[0].name == "noop"
        assert tasks_arg[1].name == "noop2"


def test_matrix_model_roles() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        system_message = "mock system message"
        model_roles1 = {
            "mark": "mockllm/mock-mark1",
            "conartist": "mockllm/mock-conartist1",
        }
        model_roles2 = {
            "mark": "mockllm/mock-mark2",
            "conartist": ModelConfig(
                name="mockllm/mock-conartist2",
                config=[GenerateConfig(system_message=system_message)],
            ),
        }
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        model_roles=[model_roles1, model_roles2],
                        tasks=[
                            TaskConfig(
                                name="task_with_model_roles",
                                file=str(task_file.absolute()),
                            )
                        ],
                    ),
                ],
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


def test_task_model_roles() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        system_message = "mock system message"
        model_roles1 = {
            "mark": "mockllm/mock-mark1",
            "conartist": "mockllm/mock-conartist1",
        }
        model_roles2 = {
            "mark": "mockllm/mock-mark2",
            "conartist": ModelConfig(
                name="mockllm/mock-conartist2",
                config=[GenerateConfig(system_message=system_message)],
            ),
        }
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="task_with_model_roles",
                                file=str(task_file.absolute()),
                                model_roles=[model_roles1, model_roles2],
                            )
                        ],
                    ),
                ],
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


def test_multiple_model_roles_error() -> None:
    with pytest.raises(
        ValueError, match="Only one of matrix and task may specify model_roles"
    ):
        system_message = "mock system message"
        model_roles1 = {
            "mark": "mockllm/mock-mark1",
            "conartist": "mockllm/mock-conartist1",
        }
        model_roles2 = {
            "mark": "mockllm/mock-mark2",
            "conartist": ModelConfig(
                name="mockllm/mock-conartist2",
                config=[GenerateConfig(system_message=system_message)],
            ),
        }
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        model_roles=[model_roles1, model_roles2],
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="task_with_model_roles",
                                file=str(task_file.absolute()),
                                model_roles=[model_roles1, model_roles2],
                            )
                        ],
                    ),
                ],
            )
        )


def test_matrix_solvers() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        solvers=[
                            SolverConfig(
                                name="inspect_ai/system_message",
                                args=[
                                    {"template": "test system message"},
                                    {"template": "another test system message"},
                                ],
                            ),
                            [
                                SolverConfig(
                                    name="inspect_ai/system_message",
                                    args=[{"template": "test system message"}],
                                ),
                                SolverConfig(name="inspect_ai/generate"),
                            ],
                            AgentConfig(name="inspect_ai/react"),
                        ],
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                            )
                        ],
                    ),
                ],
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 4
        # solvers are functions, so not simple to verify


def test_multiple_solver_args_error() -> None:
    with pytest.raises(
        ValueError, match="chained solvers may not provide multiple sets of args"
    ):
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        solvers=[
                            SolverConfig(
                                name="inspect_ai/system_message",
                                args=[
                                    {"template": "test system message"},
                                    {"template": "another test system message"},
                                ],
                            ),
                            [
                                SolverConfig(
                                    name="inspect_ai/system_message",
                                    args=[
                                        {"template": "test system message"},
                                        {"template": "another test system message"},
                                    ],
                                ),
                                SolverConfig(name="inspect_ai/generate"),
                            ],
                            AgentConfig(name="inspect_ai/react"),
                        ],
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                            )
                        ],
                    ),
                ],
            )
        )


def test_task_solvers() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        tasks=[
                            TaskConfig(
                                name="noop",
                                file=str(task_file.absolute()),
                                solvers=[
                                    SolverConfig(
                                        name="inspect_ai/system_message",
                                        args=[
                                            {"template": "test system message"},
                                            {"template": "another test system message"},
                                        ],
                                    ),
                                    [
                                        SolverConfig(
                                            name="inspect_ai/system_message",
                                            args=[{"template": "test system message"}],
                                        ),
                                        SolverConfig(name="inspect_ai/generate"),
                                    ],
                                    AgentConfig(name="inspect_ai/react"),
                                ],
                            )
                        ],
                    ),
                ],
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 4
        # solvers are functions, so not simple to verify


def test_multiple_solvers_error() -> None:
    with pytest.raises(
        ValueError, match="Only one of matrix and task may specify solvers"
    ):
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="test_log_dir"),
                matrix=[
                    Matrix(
                        models=[ModelConfig(name="mockllm/mock-llm")],
                        solvers=[SolverConfig(name="inspect_ai/generate")],
                        tasks=[
                            TaskConfig(
                                name="task_with_model_roles",
                                file=str(task_file.absolute()),
                                solvers=[SolverConfig(name="inspect_ai/generate")],
                            )
                        ],
                    ),
                ],
            )
        )
