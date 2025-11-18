import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_flow import FlowJob
from inspect_flow._config.load import ConfigOptions, load_config
from inspect_flow._launcher.launch import _new_log_dir, launch


def test_launch() -> None:
    with patch("subprocess.run") as mock_run:
        launch(config=FlowJob(log_dir="logs", tasks=["task_name"]))

        assert mock_run.call_count == 3
        args = mock_run.mock_calls[2].args[0]
        assert len(args) == 2
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


def test_launch_handles_subprocess_error() -> None:
    with (
        patch("subprocess.run") as mock_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        # Configure the third subprocess.run call to raise CalledProcessError
        mock_run.side_effect = [
            None,  # First call succeeds
            None,  # Second call succeeds
            subprocess.CalledProcessError(42, "cmd"),  # Third call fails
        ]

        launch(config=FlowJob(log_dir="logs", tasks=["task_name"]))

    # Verify sys.exit was called with the subprocess's return code
    assert exc_info.value.code == 42


def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("myenv1", raising=False)
    monkeypatch.delenv("myenv2", raising=False)

    with patch("subprocess.run") as mock_run:
        launch(
            config=FlowJob(
                log_dir="logs",
                tasks=["task_name"],
                env={"myenv1": "value1", "myenv2": "value2"},
            )
        )

    assert mock_run.call_count == 3
    env = mock_run.mock_calls[2].kwargs["env"]
    assert env["myenv1"] == "value1"
    assert env["myenv2"] == "value2"


def test_relative_log_dir() -> None:
    log_dir = "./logs/flow"
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(
            config=FlowJob(
                log_dir=log_dir,
                tasks=["task_name"],
            )
        )
    mock_venv.assert_called_once()
    assert mock_venv.mock_calls[0].args[0].log_dir == str(Path(log_dir).resolve())
    assert mock_run.call_count == 1


def test_s3() -> None:
    log_dir = "s3://my-bucket/flow-logs"
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(
            config=FlowJob(
                log_dir=log_dir,
                tasks=["task_name"],
            )
        )
    mock_venv.assert_called_once()
    assert mock_venv.mock_calls[0].args[0].log_dir == log_dir
    assert mock_run.call_count == 1


def test_config_relative_log_dir() -> None:
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        job = load_config("./tests/config/e2e_test_flow.py")
        launch(config=job)

    mock_venv.assert_called_once()
    assert job.log_dir
    expected_log_dir = Path("./tests/config/") / job.log_dir
    assert mock_venv.mock_calls[0].args[0].log_dir == str(expected_log_dir)
    assert mock_run.call_count == 1


def test_new_log_dir() -> None:
    with patch("inspect_flow._launcher.launch.exists") as mock_exists:
        mock_exists.return_value = False
        assert _new_log_dir("log_dir") == "log_dir"
        assert mock_exists.call_count == 1
    with patch("inspect_flow._launcher.launch.exists") as mock_exists:
        mock_exists.side_effect = [True, True, False]
        assert _new_log_dir("log_dir") == "log_dir_2"
        assert mock_exists.call_count == 3
    with patch("inspect_flow._launcher.launch.exists") as mock_exists:
        mock_exists.side_effect = [True, True, False]
        assert _new_log_dir("log_dir_12") == "log_dir_14"
        assert mock_exists.call_count == 3


def test_launch_new_log_dir() -> None:
    log_dir = "/etc/logs/flow"
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
        patch("inspect_flow._launcher.launch.exists") as mock_exists,
    ):
        mock_exists.side_effect = [True, True, False]
        launch(
            config=FlowJob(
                log_dir=log_dir,
                new_log_dir=True,
                tasks=["task_name"],
            )
        )
    mock_venv.assert_called_once()
    assert mock_exists.call_count == 3
    assert mock_venv.mock_calls[0].args[0].log_dir == log_dir + "_2"
    assert mock_run.call_count == 1


def test_relative_bundle_dir() -> None:
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        job = load_config(
            "./tests/config/e2e_test_flow.py",
            config_options=ConfigOptions(overrides=["options.bundle_dir=bundle_dir"]),
        )
        launch(config=job)

    mock_venv.assert_called_once()
    job: FlowJob = mock_venv.mock_calls[0].args[0]
    assert job.options
    assert (
        job.options.bundle_dir == Path("tests/config/bundle_dir").resolve().as_posix()
    )
    assert mock_run.call_count == 1
