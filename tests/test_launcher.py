import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai import Task
from inspect_ai.model import get_model
from inspect_flow import FlowSpec
from inspect_flow._api.api import load_spec
from inspect_flow._config.load import ConfigOptions, int_load_spec
from inspect_flow._launcher.launch import launch
from inspect_flow._launcher.venv import _check_spec_for_venv
from inspect_flow._types.flow_types import FlowSolver, FlowTask
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL

from tests.config.inspect_objects_flow import a_agent, a_scorer, a_solver
from tests.conftest import MockVenvSubprocess

CREATE_VENV_RUN_CALLS = 4


def test_launch_inproc() -> None:
    with (
        patch("inspect_flow._launcher.inproc.run_eval_set") as mock_run_eval_set,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )

        launch(
            spec=FlowSpec(execution_type="inproc", log_dir="logs", tasks=["task_name"]),
            base_dir=".",
        )

    assert mock_run.call_count == 2
    mock_run_eval_set.assert_called_once()


def test_launch_venv(mock_venv_subprocess: MockVenvSubprocess) -> None:
    launch(
        spec=FlowSpec(execution_type="venv", log_dir="logs", tasks=["task_name"]),
        base_dir=".",
    )

    # subprocess.run is called for venv setup (uv sync, pip install, etc.)
    assert mock_venv_subprocess.run.call_count == CREATE_VENV_RUN_CALLS

    # subprocess.Popen is called once to launch the Python process
    mock_venv_subprocess.popen.assert_called_once()
    args = mock_venv_subprocess.popen.call_args.args[0]
    assert len(args) == 8
    assert str(args[0]).endswith("/.venv/bin/python")
    assert args[1] == str(
        (
            Path(__file__).parents[1] / "src" / "inspect_flow" / "_runner" / "run.py"
        ).resolve()
    )
    assert args[2] == "--file"
    assert "flow.yaml" in args[3]
    assert args[4] == "--base-dir"
    assert args[5] == Path.cwd().as_posix()
    assert args[6] == "--log-level"
    assert args[7] == DEFAULT_LOG_LEVEL


def test_env(
    mock_venv_subprocess: MockVenvSubprocess,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("myenv1", raising=False)
    monkeypatch.delenv("myenv2", raising=False)

    launch(
        spec=FlowSpec(
            execution_type="venv",
            log_dir="logs",
            tasks=["task_name"],
            env={"myenv1": "value1", "myenv2": "value2"},
        ),
        base_dir=".",
    )

    assert mock_venv_subprocess.run.call_count == CREATE_VENV_RUN_CALLS
    mock_venv_subprocess.popen.assert_called_once()
    env = mock_venv_subprocess.popen.call_args.kwargs["env"]
    assert env["myenv1"] == "value1"
    assert env["myenv2"] == "value2"


def test_env_inproc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("myenv1", raising=False)
    monkeypatch.delenv("myenv2", raising=False)

    with patch("inspect_flow._launcher.inproc.run_eval_set"):
        launch(
            spec=FlowSpec(
                execution_type="inproc",
                log_dir="logs",
                tasks=["task_name"],
                env={"myenv1": "value1", "myenv2": "value2"},
            ),
            base_dir=".",
        )
    assert os.environ["myenv1"] == "value1"
    assert os.environ["myenv2"] == "value2"


def test_s3(mock_venv_subprocess: MockVenvSubprocess) -> None:
    log_dir = "s3://my-bucket/flow-logs"
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        launch(
            spec=FlowSpec(
                execution_type="venv",
                log_dir=log_dir,
                tasks=["task_name"],
            ),
            base_dir=".",
        )
    mock_create_venv.assert_called_once()
    assert mock_create_venv.mock_calls[0].args[0].log_dir == log_dir
    mock_venv_subprocess.popen.assert_called_once()


def test_config_relative_log_dir(mock_venv_subprocess: MockVenvSubprocess) -> None:
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        spec = load_spec("./tests/config/e2e_test_flow.py")
        spec.execution_type = "venv"
        assert spec.log_dir
        expected_log_dir = Path("./tests/config/") / spec.log_dir
        launch(
            spec=spec,
            base_dir="./tests/config/",
        )

    mock_create_venv.assert_called_once()
    assert spec.log_dir
    assert (
        mock_create_venv.mock_calls[0].args[0].log_dir
        == expected_log_dir.resolve().as_posix()
    )
    mock_venv_subprocess.popen.assert_called_once()


def test_relative_bundle_dir(mock_venv_subprocess: MockVenvSubprocess) -> None:
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        spec = int_load_spec(
            "./tests/config/e2e_test_flow.py",
            options=ConfigOptions(
                overrides=[
                    "options.bundle_dir=bundle_dir",
                    "options.bundle_url_mappings.bundle_dir=http://example.com/bundle",
                ]
            ),
        )
        spec.execution_type = "venv"
        launch(
            spec=spec,
            base_dir="tests/config/",
        )

    mock_create_venv.assert_called_once()
    spec: FlowSpec = mock_create_venv.mock_calls[0].args[0]
    absolute_path = Path("tests/config/bundle_dir").resolve().as_posix()
    assert spec.options
    assert spec.options.bundle_dir == absolute_path
    assert spec.options.bundle_url_mappings
    assert absolute_path in spec.options.bundle_url_mappings
    mock_venv_subprocess.popen.assert_called_once()


def test_bundle_dir(mock_venv_subprocess: MockVenvSubprocess) -> None:
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        spec = int_load_spec(
            "./tests/config/e2e_test_flow.py",
            options=ConfigOptions(
                overrides=[
                    "options.bundle_dir=bundle_dir",
                ]
            ),
        )
        spec.execution_type = "venv"
        launch(
            spec=spec,
            base_dir="tests/config/",
        )

    mock_create_venv.assert_called_once()
    spec: FlowSpec = mock_create_venv.mock_calls[0].args[0]
    absolute_path = Path("tests/config/bundle_dir").resolve().as_posix()
    assert spec.options
    assert spec.options.bundle_dir == absolute_path
    mock_venv_subprocess.popen.assert_called_once()


def test_259_dot_env(mock_venv_subprocess: MockVenvSubprocess) -> None:
    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[
            "local_eval/noop",
        ],
    )

    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        launch(spec=spec, base_dir="./tests/config/")
    mock_create_venv.assert_called_once()
    launch_env = mock_create_venv.mock_calls[0].kwargs["env"]
    assert launch_env["TEST_ENV_VAR"] == "test_value"

    # Now test with no_dotenv=True
    mock_venv_subprocess.popen.reset_mock()
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        launch(spec=spec, base_dir="./tests/config/", no_dotenv=True)
    mock_create_venv.assert_called_once()
    launch_env = mock_create_venv.mock_calls[0].kwargs["env"]
    assert "TEST_ENV_VAR" not in launch_env


def test_no_log_dir() -> None:
    spec = FlowSpec()
    with pytest.raises(ValueError) as e:
        launch(
            spec=spec,
            base_dir=".",
        )
    assert "log_dir must be set" in str(e.value)


def test_instantiated_venv_error() -> None:
    spec = FlowSpec(execution_type="venv", log_dir="logs", tasks=[Task()])
    with pytest.raises(ValueError) as e:
        launch(spec=spec, base_dir=".")
    assert "already-instantiated Task object" in str(e.value)

    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[FlowTask(model=get_model("mockllm/mock-llm1"))],
    )
    with pytest.raises(ValueError) as e:
        launch(spec=spec, base_dir=".")
    assert "already-instantiated Model object" in str(e.value)

    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[FlowTask(scorer=a_scorer())],
    )
    with pytest.raises(ValueError) as e:
        launch(spec=spec, base_dir=".")
    assert "already-instantiated Scorer object" in str(e.value)

    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[FlowTask(solver=[a_solver()])],
    )
    with pytest.raises(ValueError) as e:
        launch(spec=spec, base_dir=".")
    assert "already-instantiated Solver or Agent" in str(e.value)

    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[FlowTask(solver=a_agent())],
    )
    with pytest.raises(ValueError) as e:
        launch(spec=spec, base_dir=".")
    assert "already-instantiated Solver or Agent" in str(e.value)

    # Valid case should not throw
    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[FlowTask(solver=[FlowSolver(name="solver_name")])],
    )
    _check_spec_for_venv(spec)


def test_flow_process_error(mock_venv_subprocess: MockVenvSubprocess) -> None:
    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        tasks=[
            "local_eval/noop",
        ],
    )

    mock_venv_subprocess.popen.return_value.returncode = 123

    with (
        patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv,
        pytest.raises(subprocess.CalledProcessError) as e,
    ):
        launch(spec=spec, base_dir="./tests/config/")
    mock_create_venv.assert_called_once()
    assert e.value.returncode == 123
