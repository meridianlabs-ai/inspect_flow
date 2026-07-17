import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.client import BaseClient
from click.testing import CliRunner
from inspect_ai import ScannerConfig, Task
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import get_model
from inspect_flow import FlowSpec
from inspect_flow._api.api import init, load_spec, run
from inspect_flow._config.load import ConfigOptions, int_load_spec
from inspect_flow._config.write import write_config_file
from inspect_flow._display.display import DEFAULT_DISPLAY_TYPE
from inspect_flow._launcher.launch import launch
from inspect_flow._launcher.venv import _check_spec_for_venv, _create_venv
from inspect_flow._runner.cli import runner
from inspect_flow._runner.run import LaunchResult
from inspect_flow._types.flow_types import FlowOptions, FlowSolver, FlowTask
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.subprocess_util import RUN_RESULT_FILE_ENV, read_run_result
from inspect_scout import ScannerSpec
from local_eval.my_scanners import keyword_scanner

from tests.config.inspect_objects_flow import a_agent, a_scorer, a_solver
from tests.conftest import MockVenvSubprocess, mock_call_arg

CREATE_VENV_RUN_CALLS = 4

_TASK = "tests/local_eval/src/local_eval/noop.py@noop"


def test_launch_inproc() -> None:
    with (
        patch("inspect_flow._launcher.inproc.run_eval_set") as mock_run_eval_set,
        patch("subprocess.run") as mock_run,
    ):
        mock_run_eval_set.return_value = LaunchResult(success=True, logs=[])
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
    assert len(args) == 11
    assert str(args[0]).endswith("/.venv/bin/python")
    assert args[1] == str(
        (
            Path(__file__).parents[1] / "src" / "inspect_flow" / "_runner" / "cli.py"
        ).resolve()
    )
    assert args[2] == "run"
    assert args[3] == "--file"
    assert "flow.yaml" in args[4]
    assert args[5] == "--base-dir"
    assert args[6] == Path.cwd().as_posix()
    assert args[7] == "--log-level"
    assert args[8] == DEFAULT_LOG_LEVEL
    assert args[9] == "--display"
    assert args[10] == DEFAULT_DISPLAY_TYPE


@pytest.mark.parametrize("child_success", [True, False])
def test_launch_venv_returns_subprocess_success(
    mock_venv_subprocess: MockVenvSubprocess, child_success: bool
) -> None:
    # The child writes its success flag to the per-run result file before exiting;
    # the parent reads it back and returns it (with empty logs, in the child).
    def write_result() -> None:
        env = mock_venv_subprocess.popen.call_args.kwargs["env"]
        Path(env[RUN_RESULT_FILE_ENV]).write_text(json.dumps({"ok": child_success}))

    mock_venv_subprocess.popen.return_value.wait.side_effect = write_result

    success, logs = launch(
        spec=FlowSpec(execution_type="venv", log_dir="logs", tasks=["task_name"]),
        base_dir=".",
    )

    assert success is child_success
    assert logs == []


def test_launch_venv_missing_result_raises(
    mock_venv_subprocess: MockVenvSubprocess,
) -> None:
    # Child exits cleanly but never writes a result; the parent must not silently
    # report success or failure.
    mock_venv_subprocess.popen.return_value.wait.side_effect = None
    with pytest.raises(RuntimeError, match="without reporting a result"):
        launch(
            spec=FlowSpec(execution_type="venv", log_dir="logs", tasks=["task_name"]),
            base_dir=".",
        )


@pytest.mark.parametrize("eval_set_success", [True, False])
def test_runner_run_writes_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, eval_set_success: bool
) -> None:
    spec = FlowSpec(
        log_dir=str(tmp_path / "logs"),
        store="none",
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )
    config_file = write_config_file(spec)
    result_path = tmp_path / "run_result.json"
    monkeypatch.setenv(RUN_RESULT_FILE_ENV, str(result_path))

    with patch(
        "inspect_flow._runner.cli.run_eval_set",
        return_value=LaunchResult(success=eval_set_success, logs=[]),
    ):
        result = CliRunner().invoke(
            runner,
            ["run", "--file", config_file, "--base-dir", "."],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert read_run_result(str(result_path)).ok is eval_set_success


@pytest.mark.parametrize("is_complete", [True, False])
def test_runner_check_writes_is_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, is_complete: bool
) -> None:
    spec = FlowSpec(
        log_dir=str(tmp_path / "logs"),
        store="none",
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )
    config_file = write_config_file(spec)
    result_path = tmp_path / "run_result.json"
    monkeypatch.setenv(RUN_RESULT_FILE_ENV, str(result_path))

    with patch(
        "inspect_flow._runner.cli.check_eval_set",
        return_value=MagicMock(is_complete=is_complete),
    ):
        result = CliRunner().invoke(
            runner,
            ["check", "--file", config_file, "--base-dir", "."],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert read_run_result(str(result_path)).ok is is_complete


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

    with patch(
        "inspect_flow._launcher.inproc.run_eval_set",
        return_value=LaunchResult(success=True, logs=[]),
    ):
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


def test_s3(mock_s3: BaseClient, mock_venv_subprocess: MockVenvSubprocess) -> None:
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
    assert mock_call_arg(_create_venv, mock_create_venv, "spec").log_dir == log_dir
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
        mock_call_arg(_create_venv, mock_create_venv, "spec").log_dir
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
    spec = mock_call_arg(_create_venv, mock_create_venv, "spec")
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
    spec = mock_call_arg(_create_venv, mock_create_venv, "spec")
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

    # init with directory loads .env into os.environ and the venv subprocess env
    init(display="plain", dotenv_base_dir="./tests/config/")
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        run(spec=spec, base_dir="./tests/config/")
    mock_create_venv.assert_called_once()
    launch_env = mock_call_arg(_create_venv, mock_create_venv, "env")
    assert launch_env["TEST_ENV_VAR"] == "test_value"
    assert os.environ["TEST_ENV_VAR"] == "test_value"

    # init with a file path uses the file's parent directory
    del os.environ["TEST_ENV_VAR"]
    init(display="plain", dotenv_base_dir="./tests/config/mock_flow.py")
    assert os.environ["TEST_ENV_VAR"] == "test_value"

    # init with dotenv_base_dir=None skips .env loading
    del os.environ["TEST_ENV_VAR"]
    init(display="plain", dotenv_base_dir=None)
    mock_venv_subprocess.popen.reset_mock()
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        run(spec=spec, base_dir="./tests/config/")
    mock_create_venv.assert_called_once()
    launch_env = mock_call_arg(_create_venv, mock_create_venv, "env")
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


def test_live_scanner_venv_error() -> None:
    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        options=FlowOptions(scanner=ScannerConfig(scanners=[keyword_scanner()])),
        tasks=["local_eval/noop"],
    )
    with pytest.raises(ValueError) as e:
        launch(spec=spec, base_dir=".")
    assert "already-instantiated Scanner objects" in str(e.value)

    # Any Sequence of live scanners is rejected, not just a list
    spec.options = FlowOptions(scanner=ScannerConfig(scanners=(keyword_scanner(),)))
    with pytest.raises(ValueError, match="already-instantiated Scanner objects"):
        _check_spec_for_venv(spec)

    # As are scout's (name, Scanner) tuple entries
    spec.options = FlowOptions(
        scanner=ScannerConfig(scanners=[("kw", keyword_scanner())])
    )
    with pytest.raises(ValueError, match="already-instantiated Scanner objects"):
        _check_spec_for_venv(spec)

    # A registry-name string entry gets a shape error, not the live-object one
    spec.options = FlowOptions(scanner=ScannerConfig(scanners=["keyword_scanner"]))
    with pytest.raises(ValueError, match="entries must be scanners"):
        _check_spec_for_venv(spec)

    # A live Model in the scanner config is also rejected
    spec.options = FlowOptions(
        scanner=ScannerConfig(
            scanners=[{"name": "keyword_scanner"}], model=get_model("mockllm/model")
        )
    )
    with pytest.raises(ValueError, match="Model object as the ScannerConfig model"):
        _check_spec_for_venv(spec)

    # A bare scanners value (not wrapped in a sequence) is rejected — live or
    # spec-form, its serialized form is ambiguous with a dict of named scanners
    spec.options = FlowOptions(scanner=ScannerConfig(scanners=keyword_scanner()))
    with pytest.raises(ValueError, match="Wrap a single scanner in a list"):
        _check_spec_for_venv(spec)
    spec.options = FlowOptions(
        scanner=ScannerConfig(scanners=ScannerSpec(name="keyword_scanner"))
    )
    with pytest.raises(ValueError, match="Wrap a single scanner in a list"):
        _check_spec_for_venv(spec)

    # A bare spec dict (e.g. a YAML mapping missing its list dash) is rejected
    # rather than misread as a dict of named scanners
    spec.options = FlowOptions(
        scanner=ScannerConfig(scanners={"name": "keyword_scanner"})
    )
    with pytest.raises(ValueError, match="dict values must be scanners"):
        _check_spec_for_venv(spec)

    # As is a named-scanner dict whose value is missing/invalid
    spec.options = FlowOptions(scanner=ScannerConfig(scanners={"kw": None}))
    with pytest.raises(ValueError, match="dict values must be scanners"):
        _check_spec_for_venv(spec)

    # A live Model in the scanner config model_roles is also rejected
    spec.options = FlowOptions(
        scanner=ScannerConfig(
            scanners=[{"name": "keyword_scanner"}],
            model_roles={"grader": get_model("mockllm/model")},
        )
    )
    with pytest.raises(ValueError, match="Model object as the ScannerConfig model"):
        _check_spec_for_venv(spec)

    # A config file path or a config of ScannerSpecs (dicts or instances)
    # should not throw
    spec.options = FlowOptions(scanner="tests/config/scanners.yaml")
    _check_spec_for_venv(spec)
    spec.options = FlowOptions(
        scanner=ScannerConfig(scanners=[{"name": "keyword_scanner"}])
    )
    _check_spec_for_venv(spec)
    spec.options = FlowOptions(
        scanner=ScannerConfig(scanners=[ScannerSpec(name="keyword_scanner")])
    )
    _check_spec_for_venv(spec)
    spec.options = FlowOptions(
        scanner=ScannerConfig(scanners={"kw": {"name": "keyword_scanner"}})
    )
    _check_spec_for_venv(spec)


def test_relative_scanner_path(mock_venv_subprocess: MockVenvSubprocess) -> None:
    with patch("inspect_flow._launcher.venv._create_venv") as mock_create_venv:
        spec = int_load_spec(
            "./tests/config/e2e_test_flow.py",
            options=ConfigOptions(overrides=["options.scanner=scanners.yaml"]),
        )
        spec.execution_type = "venv"
        launch(
            spec=spec,
            base_dir="tests/config/",
        )

    mock_create_venv.assert_called_once()
    spec = mock_call_arg(_create_venv, mock_create_venv, "spec")
    assert spec.options
    assert (
        spec.options.scanner == Path("tests/config/scanners.yaml").resolve().as_posix()
    )
    mock_venv_subprocess.popen.assert_called_once()


def test_missing_scanner_path_fails_at_launch() -> None:
    # A typo'd scanner config path fails before the venv is built
    spec = FlowSpec(
        execution_type="venv",
        log_dir="logs",
        options=FlowOptions(scanner="no_such_scanners.yaml"),
        tasks=["local_eval/noop"],
    )
    with pytest.raises(PrerequisiteError, match="does not exist"):
        launch(spec=spec, base_dir="tests/config/")


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
