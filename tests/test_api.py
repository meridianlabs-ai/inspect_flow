import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_flow._api import api as api_module
from inspect_flow._types.flow_types import FlowSpec, FlowTask, not_given
from inspect_flow._util.data import LAST_LOG_DIR_KEY, read_data
from inspect_flow.api import RunResult, check, config, init, load_spec, run, store_get

from tests.test_helpers.config_helpers import validate_config

_TASK = "tests/local_eval/src/local_eval/noop.py@noop"


@pytest.fixture(autouse=True)
def reset_initialized() -> None:
    """Reset the _initialized flag so _ensure_init fires each test."""
    api_module._initialized = False


def test_258_run_includes() -> None:
    spec = FlowSpec(
        includes=["defaults_flow.py"],
        log_dir="logs",
        log_dir_create_unique=False,
        tasks=[
            "local_eval/noop",
            FlowTask(name="local_eval/noop", model="{defaults[model][name]}"),
        ],
    )
    with patch("inspect_flow._api.api.launch") as mock_launch:
        mock_launch.return_value = (True, [])
        run(spec=spec, base_dir="./tests/config/")
    mock_launch.assert_called_once()
    launch_spec = mock_launch.mock_calls[0].kwargs["spec"]
    assert launch_spec.includes == not_given
    validate_config(launch_spec, "run_includes.yaml")


def test_config() -> None:
    spec = FlowSpec(
        tasks=[
            "local_eval/noop",
        ],
    )
    dump = config(spec=spec, base_dir="./tests/config/")
    expected_dump = """tasks:
- name: local_eval/noop
"""
    assert dump == expected_dump


def test_ensure_init_loads_dotenv_from_base_dir(tmp_path: Path) -> None:
    """When init() is not called explicitly, _ensure_init should load .env from base_dir."""
    os.environ.pop("TEST_ENV_VAR", None)
    spec = FlowSpec(log_dir=str(tmp_path / "logs"), tasks=["local_eval/noop"])
    with patch("inspect_flow._api.api.launch") as mock_launch:
        mock_launch.return_value = (True, [])
        run(spec=spec, base_dir="./tests/config/")
    assert os.environ.get("TEST_ENV_VAR") == "test_value"
    del os.environ["TEST_ENV_VAR"]


def test_ensure_init_loads_dotenv_from_file() -> None:
    """When init() is not called explicitly, _ensure_init should load .env from spec file dir."""
    os.environ.pop("TEST_ENV_VAR", None)
    load_spec(file="./tests/config/mock_flow.py")
    assert os.environ.get("TEST_ENV_VAR") == "test_value"
    del os.environ["TEST_ENV_VAR"]


def test_init_s3_dotenv_falls_back_to_cwd() -> None:
    """S3 base_dir is non-local, so init falls back to loading .env from cwd."""
    with patch("inspect_flow._api.api.load_dotenv") as mock_load:
        init(dotenv_base_dir="s3://bucket/path")
    mock_load.assert_called_once()


def test_store_get_raises_when_no_store(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Could not open store"):
        store_get(store=str(tmp_path / "nonexistent"), create=False)


def test_resume(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        store="none",
        tasks=["local_eval/noop"],
    )

    with (
        patch("inspect_flow._launcher.inproc.run_eval_set") as mock_run_eval_set,
        patch("subprocess.run") as mock_subprocess,
    ):
        mock_run_eval_set.return_value = (True, [])
        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=""
        )

        # First run saves log_dir
        run(spec=spec, base_dir="./tests/config/")
        first_log_dir = mock_run_eval_set.call_args.args[0].log_dir

        # Second run with resume reuses the same log_dir
        resume_spec = FlowSpec(
            log_dir="should_be_overridden",
            store="none",
            tasks=["local_eval/noop"],
        )
        run(spec=resume_spec, base_dir="./tests/config/", resume=True)
        resumed_log_dir = mock_run_eval_set.call_args.args[0].log_dir

    assert resumed_log_dir == first_log_dir
    assert read_data(LAST_LOG_DIR_KEY) == first_log_dir


def test_resume_ignores_log_dir_create_unique(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        log_dir_create_unique=True,
        store="none",
        tasks=["local_eval/noop"],
    )

    with (
        patch("inspect_flow._launcher.inproc.run_eval_set") as mock_run_eval_set,
        patch("subprocess.run") as mock_subprocess,
    ):
        mock_run_eval_set.return_value = (True, [])
        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=""
        )

        # First run with log_dir_create_unique creates a timestamped subdir
        run(spec=spec, base_dir="./tests/config/")
        first_log_dir = mock_run_eval_set.call_args.args[0].log_dir

        # Second run with resume should reuse the exact same log_dir,
        # even when log_dir_create_unique is set on the spec
        resume_spec = FlowSpec(
            log_dir="should_be_overridden",
            log_dir_create_unique=True,
            store="none",
            tasks=["local_eval/noop"],
        )
        run(spec=resume_spec, base_dir="./tests/config/", resume=True)
        resumed_log_dir = mock_run_eval_set.call_args.args[0].log_dir

    assert resumed_log_dir == first_log_dir


def test_run_returns_result(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        store="none",
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )

    result = run(spec=spec, base_dir=".")

    assert isinstance(result, RunResult)
    assert result.success
    assert len(result.logs) == 1
    assert result.logs[0].status == "success"
    assert Path(result.log_dir).is_absolute()
    assert Path(result.log_dir).name == "logs"


def test_run_dry_run_returns_result(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        store="none",
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )

    result = run(spec=spec, base_dir=".", dry_run=True)

    assert isinstance(result, RunResult)
    assert not result.success
    assert result.logs == []
    assert Path(result.log_dir).is_absolute()
    assert Path(result.log_dir).name == "logs"


def test_check_disables_log_dir_create_unique(tmp_path: Path) -> None:
    spec = FlowSpec(
        log_dir=str(tmp_path / "logs"),
        log_dir_create_unique=True,
        store="none",
        tasks=["local_eval/noop"],
    )

    with patch("inspect_flow._api.api.launch_check") as mock_check:
        check(spec=spec, base_dir="./tests/config/")
        checked_spec = mock_check.call_args.kwargs["spec"]

    assert not checked_spec.log_dir_create_unique
