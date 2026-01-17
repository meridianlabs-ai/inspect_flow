import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai._util.logger import LogHandlerVar
from inspect_flow import FlowSpec
from inspect_flow._api.api import load_spec
from inspect_flow._config.load import ConfigOptions, int_load_spec
from inspect_flow._launcher.launch import launch
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging

CREATE_VENV_RUN_CALLS = 4


def test_launch() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )
        launch(
            spec=FlowSpec(log_dir="logs", tasks=["task_name"]),
            base_dir=".",
        )

        assert mock_run.call_count == CREATE_VENV_RUN_CALLS + 1
        args = mock_run.mock_calls[CREATE_VENV_RUN_CALLS].args[0]
        assert len(args) == 8
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
        assert args[2] == "--file"
        assert "flow.yaml" in args[3]
        assert args[4] == "--base-dir"
        assert args[5] == Path.cwd().as_posix()
        assert args[6] == "--log-level"
        assert args[7] == DEFAULT_LOG_LEVEL


def test_launch_venv() -> None:
    log_handler: LogHandlerVar = {"handler": None}
    init_flow_logging(log_level="warning", log_handler_var=log_handler)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )
        launch(
            spec=FlowSpec(log_dir="logs", tasks=["task_name"]),
            base_dir=".",
            venv=True,
        )

        assert mock_run.call_count == 1
        args = mock_run.mock_calls[0].args[0]
        assert len(args) == 8
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
        assert args[2] == "--file"
        assert args[3] == "flow.yaml"
        assert args[4] == "--base-dir"
        assert args[5] == Path.cwd().as_posix()
        assert args[6] == "--log-level"
        assert args[7] == "warning"


def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("myenv1", raising=False)
    monkeypatch.delenv("myenv2", raising=False)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )

        launch(
            spec=FlowSpec(
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
            spec=FlowSpec(
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
        spec = load_spec("./tests/config/e2e_test_flow.py")
        assert spec.log_dir
        expected_log_dir = Path("./tests/config/") / spec.log_dir
        launch(
            spec=spec,
            base_dir="./tests/config/",
        )

    mock_venv.assert_called_once()
    assert spec.log_dir
    assert (
        mock_venv.mock_calls[0].args[0].log_dir == expected_log_dir.resolve().as_posix()
    )
    assert mock_run.call_count == 1


def test_relative_bundle_dir() -> None:
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        spec = int_load_spec(
            "./tests/config/e2e_test_flow.py",
            options=ConfigOptions(
                overrides=[
                    "options.bundle_dir=bundle_dir",
                    "options.bundle_url_mappings.bundle_dir=http://example.com/bundle}",
                ]
            ),
        )
        launch(
            spec=spec,
            base_dir="tests/config/",
        )

    mock_venv.assert_called_once()
    spec: FlowSpec = mock_venv.mock_calls[0].args[0]
    absolute_path = Path("tests/config/bundle_dir").resolve().as_posix()
    assert spec.options
    assert spec.options.bundle_dir == absolute_path
    assert spec.options.bundle_url_mappings
    assert absolute_path in spec.options.bundle_url_mappings
    assert mock_run.call_count == 1


def test_bundle_dir() -> None:
    with (
        patch("subprocess.run") as mock_run,
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        spec = int_load_spec(
            "./tests/config/e2e_test_flow.py",
            options=ConfigOptions(
                overrides=[
                    "options.bundle_dir=bundle_dir",
                ]
            ),
        )
        launch(
            spec=spec,
            base_dir="tests/config/",
        )

    mock_venv.assert_called_once()
    spec: FlowSpec = mock_venv.mock_calls[0].args[0]
    absolute_path = Path("tests/config/bundle_dir").resolve().as_posix()
    assert spec.options
    assert spec.options.bundle_dir == absolute_path
    assert mock_run.call_count == 1


def test_259_dot_env() -> None:
    spec = FlowSpec(
        log_dir="logs",
        tasks=[
            "local_eval/noop",
        ],
    )

    with (
        patch("subprocess.run"),
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(spec=spec, base_dir="./tests/config/")
    mock_venv.assert_called_once()
    launch_env = mock_venv.mock_calls[0].kwargs["env"]
    assert launch_env["TEST_ENV_VAR"] == "test_value"
    # Now test with no_dotenv=True
    with (
        patch("subprocess.run"),
        patch("inspect_flow._launcher.launch.create_venv") as mock_venv,
    ):
        launch(spec=spec, base_dir="./tests/config/", no_dotenv=True)
    mock_venv.assert_called_once()
    launch_env = mock_venv.mock_calls[0].kwargs["env"]
    assert "TEST_ENV_VAR" not in launch_env


def test_no_log_dir() -> None:
    spec = FlowSpec()
    with pytest.raises(ValueError) as e:
        launch(
            spec=spec,
            base_dir=".",
        )
    assert "log_dir must be set" in str(e.value)
