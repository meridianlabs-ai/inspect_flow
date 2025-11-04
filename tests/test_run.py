import os
from pathlib import Path
from unittest.mock import patch

from inspect_ai import Task
from inspect_ai.model import GenerateConfig, Model
from inspect_flow import flow_config, solvers_matrix, tasks_matrix
from inspect_flow._runner.run import run_eval_set
from inspect_flow.types import (
    FAgent,
    FConfig,
    FModel,
    FSolver,
    FTask,
)

from .test_helpers.log_helpers import init_test_logs, verify_test_logs

task_dir = (
    Path(__file__).parents[1] / "examples" / "local_eval" / "src" / "local_eval"
).resolve()
task_file = str(task_dir / "noop.py")


def test_task_with_get_model() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=[
                    FTask(
                        name=task_file + "@task_with_get_model",
                        model=FModel(name="mockllm/mock-llm"),
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

    config = FConfig(
        flow_dir=log_dir,
        tasks=tasks_matrix(
            task_file + "@noop",
            {
                "model": [
                    FModel(name="mockllm/mock-llm1"),
                    FModel(name="mockllm/mock-llm2"),
                ],
            },
        ),
    )
    run_eval_set(config=config)

    verify_test_logs(config, log_dir)


def test_model_generate_config() -> None:
    system_message = "Test System Message"
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=[
                    FTask(
                        name=task_file + "@noop",
                        model=FModel(
                            name="mockllm/mock-llm",
                            config=GenerateConfig(system_message=system_message),
                        ),
                    )
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
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=[FTask(name=task_file + "@noop")],
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
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=[
                    FTask(
                        name=task_file + "@noop",
                        model=FModel(name="mockllm/mock-llm"),
                    )
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


def test_matrix_args() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=tasks_matrix(
                    FTask(
                        name=task_file + "@task_with_params",
                        model=FModel(name="mockllm/mock-llm"),
                    ),
                    {
                        "args": [{"subset": "original"}, {"subset": "contrast"}],
                    },
                ),
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
            "conartist": FModel(
                name="mockllm/mock-conartist2",
                config=GenerateConfig(system_message=system_message),
            ),
        }
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=tasks_matrix(
                    FTask(
                        name=task_file + "@task_with_model_roles",
                        model=FModel(name="mockllm/mock-llm"),
                    ),
                    {
                        "model_roles": [model_roles1, model_roles2],
                    },
                ),
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
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=tasks_matrix(
                    FTask(
                        name=task_file + "@noop",
                        model=FModel(name="mockllm/mock-llm"),
                    ),
                    {
                        "solver": [
                            *solvers_matrix(
                                "inspect_ai/system_message",
                                {
                                    "args": [
                                        {"template": "test system message"},
                                        {"template": "another test system message"},
                                    ],
                                },
                            ),
                            [
                                FSolver(
                                    name="inspect_ai/system_message",
                                    args={"template": "test system message"},
                                ),
                                FSolver(name="inspect_ai/generate"),
                            ],
                            FAgent(name="inspect_ai/react"),
                        ],
                    },
                ),
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 4
        # solvers are functions, so not simple to verify


def test_sample_id() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=[FTask(name=task_file + "@noop", sample_id=1)],
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
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=flow_config(
                {
                    "flow_dir": "test_log_dir",
                    "tasks": str(task_dir / "three_tasks.py"),
                }
            ),
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 3
        assert tasks_arg[0].name == "noop1"
        assert tasks_arg[1].name == "noop2"
        assert tasks_arg[2].name == "noop3"


def test_config_generate_config() -> None:
    config_system_message = "Config System Message"
    task_system_message = "Task System Message"
    model_system_message = "Model System Message"
    config_temperature = 0.0
    task_temperature = 0.2
    config_max_tokens = 100

    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                config=GenerateConfig(
                    system_message=config_system_message,
                    temperature=config_temperature,
                    max_tokens=config_max_tokens,
                ),
                tasks=[
                    FTask(
                        name=task_file + "@noop",
                        config=GenerateConfig(
                            system_message=task_system_message,
                            temperature=task_temperature,
                        ),
                        model=FModel(
                            name="mockllm/mock-llm",
                            config=GenerateConfig(system_message=model_system_message),
                        ),
                    )
                ],
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


def test_dry_run():
    assert not os.environ.get("INSPECT_FLOW_DRY_RUN")
    os.environ["INSPECT_FLOW_DRY_RUN"] = "1"
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FConfig(
                flow_dir="test_log_dir",
                tasks=[
                    FTask(
                        name=task_file + "@task_with_get_model",
                        model=FModel(name="mockllm/mock-llm"),
                    )
                ],
            )
        )

    del os.environ["INSPECT_FLOW_DRY_RUN"]
    mock_eval_set.assert_not_called()
