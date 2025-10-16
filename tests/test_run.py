from pathlib import Path
from unittest.mock import patch

from inspect_ai import Task
from inspect_ai.model import GenerateConfig, Model
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.types import (
    FlowConfig,
    FlowOptions,
    Matrix,
    ModelConfig,
    TaskConfig,
)

from .test_helpers.log_helpers import init_test_logs, verify_test_logs

task_file = (
    Path(__file__).parent.parent
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
                options=FlowOptions(log_dir="get_model"),
                matrix=Matrix(
                    models=[ModelConfig(name="mockllm/mock-llm")],
                    tasks=[
                        TaskConfig(
                            name="task_with_get_model", file=str(task_file.absolute())
                        )
                    ],
                ),
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
        matrix=Matrix(
            models=[
                ModelConfig(name="mockllm/mock-llm1"),
                ModelConfig(name="mockllm/mock-llm2"),
            ],
            tasks=[TaskConfig(name="noop", file=str(task_file.absolute()))],
        ),
    )
    run_eval_set(config=config)

    verify_test_logs(config, log_dir)


def test_model_generate_config() -> None:
    system_message = "Test System Message"
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="model_generate_config"),
                matrix=Matrix(
                    models=[
                        ModelConfig(
                            name="mockllm/mock-llm",
                            config=GenerateConfig(system_message=system_message),
                        ),
                    ],
                    tasks=[TaskConfig(name="noop", file=str(task_file.absolute()))],
                ),
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
                options=FlowOptions(log_dir="model_generate_config"),
                matrix=Matrix(
                    tasks=[TaskConfig(name="noop", file=str(task_file.absolute()))],
                ),
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
        assert tasks_arg[0].model is None
