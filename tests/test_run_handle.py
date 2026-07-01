import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from inspect_flow import FlowSpec, FlowTask
from inspect_flow._launcher.launch import launch
from inspect_flow._util.run_handle import run_handle, write_run_handle

from .test_helpers.log_helpers import init_test_logs

task_file = "tests/local_eval/src/local_eval/noop.py"


def test_run_handle_contents() -> None:
    handle = run_handle("/some/log/dir")
    assert handle == {"log_dir": "/some/log/dir", "pid": os.getpid()}


def test_write_run_handle(tmp_path: Path) -> None:
    handle_file = str(tmp_path / "handle.json")
    write_run_handle(handle_file, "/some/log/dir")
    handle = json.loads(Path(handle_file).read_text())
    assert handle == {"log_dir": "/some/log/dir", "pid": os.getpid()}


def test_launch_writes_handle_file(mock_eval_set: MagicMock, tmp_path: Path) -> None:
    log_dir = init_test_logs()
    handle_file = str(tmp_path / "handle.json")
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    launch(spec=spec, base_dir=".", handle_file=handle_file)

    mock_eval_set.assert_called_once()
    handle = json.loads(Path(handle_file).read_text())
    # launch() resolves log_dir to an absolute path before writing the handle
    assert handle["log_dir"] == spec.log_dir
    assert handle["pid"] == os.getpid()


def test_launch_without_handle_file(mock_eval_set: MagicMock, tmp_path: Path) -> None:
    handle_file = tmp_path / "handle.json"
    spec = FlowSpec(
        log_dir=init_test_logs(),
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    launch(spec=spec, base_dir=".")

    mock_eval_set.assert_called_once()
    assert not handle_file.exists()
