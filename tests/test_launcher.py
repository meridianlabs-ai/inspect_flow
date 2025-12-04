import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_flow import FlowJob
from inspect_flow._api.api import load_job
from inspect_flow._config.load import ConfigOptions, int_load_job
from inspect_flow._launcher.launch import launch

CREATE_VENV_RUN_CALLS = 3


def test_launch() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )
        launch(
            job=FlowJob(log_dir="logs", tasks=["task_name"]),
            base_dir=".",
        )

        assert mock_run.call_count == CREATE_VENV_RUN_CALLS + 1
        args = mock_run.mock_calls[CREATE_VENV_RUN_CALLS].args[0]
        assert len(args) == 4
        assert str(args[0]).endswith("/.venv/bin/python")
        assert args[1] == str(
            (
                Path(__file__).parents[1]
                / "src"
                / "inspect_flow"
                / "_runner"
                / "run.py"
            ).resolve()
        )
        assert args[2] == "--base-dir"
        assert args[3] == Path.cwd().as_posix()


def test_launch_no_venv() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )
        launch(
            job=FlowJob(log_dir="logs", tasks=["task_name"]),
            base_dir=".",
            no_venv=True,
        )

        assert mock_run.call_count == 1
        args = mock_run.mock_calls[0].args[0]
        assert len(args) == 4
        assert args[0] == sys.executable
        assert args[1] == str(
            (
                Path(__file__).parents[1]
                / "src"
                / "inspect_flow"
                / "_runner"
                / "run.py"
            ).resolve()
        )
        assert args[2] == "--base-dir"
        assert args[3] == Path.cwd().as_posix()


def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("myenv1", raising=False)
    monkeypatch.delenv("myenv2", raising=False)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )

        launch(
            job=FlowJob(
                log_dir="logs",
                tasks=["task_name"],
                env={"myenv1": "value1", "myenv2": "value2"},
            ),
            base_dir=".",
        )

    assert mock_run.call_count == CREATE_VENV_RUN_CALLS + 1
    env = mock_run.mock_calls[CREATE_VENV_RUN_CALLS].kwargs["env"]
    assert env["myenv1"] == "value1"
    assert env["myenv2"] == "value2"


def test_s3() -> None:
    log_dir = "s3://my-bucket/flow-logs"
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(
            job=FlowJob(
                log_dir=log_dir,
                tasks=["task_name"],
            ),
            base_dir=".",
        )
    mock_venv.assert_called_once()
    assert mock_venv.mock_calls[0].args[0].log_dir == log_dir
    assert mock_run.call_count == 1


def test_config_relative_log_dir() -> None:
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        job = load_job("./tests/config/e2e_test_flow.py")
        assert job.log_dir
        expected_log_dir = Path("./tests/config/") / job.log_dir
        launch(
            job=job,
            base_dir="./tests/config/",
        )

    mock_venv.assert_called_once()
    assert job.log_dir
    assert (
        mock_venv.mock_calls[0].args[0].log_dir == expected_log_dir.resolve().as_posix()
    )
    assert mock_run.call_count == 1


def test_relative_bundle_dir() -> None:
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        job = int_load_job(
            "./tests/config/e2e_test_flow.py",
            options=ConfigOptions(
                overrides=[
                    "options.bundle_dir=bundle_dir",
                    "options.bundle_url_map.bundle_dir=http://example.com/bundle}",
                ]
            ),
        )
        launch(
            job=job,
            base_dir="tests/config/",
        )

    mock_venv.assert_called_once()
    job: FlowJob = mock_venv.mock_calls[0].args[0]
    absolute_path = Path("tests/config/bundle_dir").resolve().as_posix()
    assert job.options
    assert job.options.bundle_dir == absolute_path
    assert job.options.bundle_url_map
    assert absolute_path in job.options.bundle_url_map
    assert mock_run.call_count == 1


def test_259_dot_env() -> None:
    job = FlowJob(
        log_dir="logs",
        tasks=[
            "local_eval/noop",
        ],
    )

    with (
        patch("subprocess.run"),
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(job=job, base_dir="./tests/config/")
    mock_venv.assert_called_once()
    launch_env = mock_venv.mock_calls[0].kwargs["env"]
    assert launch_env["TEST_ENV_VAR"] == "test_value"
    # Now test with no_dotenv=True
    with (
        patch("subprocess.run"),
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(job=job, base_dir="./tests/config/", no_dotenv=True)
    mock_venv.assert_called_once()
    launch_env = mock_venv.mock_calls[0].kwargs["env"]
    assert "TEST_ENV_VAR" not in launch_env
