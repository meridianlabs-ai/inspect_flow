import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner
from inspect_flow._cli.check import check_command
from inspect_flow._cli.config import config_command
from inspect_flow._cli.list import list_command
from inspect_flow._cli.run import run_command
from inspect_flow._cli.store import store_command

_TASK = "tests/local_eval/src/local_eval/noop.py@noop"
_TASK_ABS = f"{Path(_TASK.split('@')[0]).resolve()}@{_TASK.split('@')[1]}"
_NOOP_SAMPLES = 2
_STORE_LOG_DIR = "tests/test_logs/logs1"


def _write_spec(tmp_path: Path, log_dir: str) -> str:
    spec_file = tmp_path / "flow.yaml"
    spec_file.write_text(
        f"log_dir: {log_dir}\n"
        "tasks:\n"
        f"  - name: {_TASK_ABS}\n"
        "    model: mockllm/mock-llm\n"
    )
    return str(spec_file)


def _invoke_json(command: Any, args: list[str]) -> Any:
    result = CliRunner().invoke(command, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_config_json(tmp_path: Path) -> None:
    spec_file = _write_spec(tmp_path, str(tmp_path / "logs"))
    data = _invoke_json(config_command, [spec_file, "--json"])
    assert data["tasks"][0]["name"].endswith("noop.py@noop")


def test_check_json_no_logs(tmp_path: Path) -> None:
    spec_file = _write_spec(tmp_path, str(tmp_path / "logs"))
    data = _invoke_json(check_command, [spec_file, "--json"])

    assert data["summary"] == {"total": 1, "complete": 0, "incomplete": 1}
    assert data["unrecognized"] == []
    (task,) = data["tasks"]
    assert task["name"].endswith("noop.py@noop")
    assert task["log_file"] is None
    assert task["samples"] == 0
    assert task["total_samples"] == _NOOP_SAMPLES
    assert task["complete"] is False


def test_check_json_with_completed_log(tmp_path: Path) -> None:
    spec_file = _write_spec(tmp_path, str(tmp_path / "logs"))
    runner = CliRunner()
    assert runner.invoke(run_command, [spec_file]).exit_code == 0

    data = _invoke_json(check_command, [spec_file, "--json"])
    assert data["summary"] == {"total": 1, "complete": 1, "incomplete": 0}
    (task,) = data["tasks"]
    assert task["log_file"] is not None
    assert task["samples"] == _NOOP_SAMPLES
    assert task["complete"] is True


def test_run_dry_run_json(tmp_path: Path) -> None:
    spec_file = _write_spec(tmp_path, str(tmp_path / "logs"))
    data = _invoke_json(run_command, [spec_file, "--dry-run", "--json"])
    assert data["summary"] == {"total": 1, "complete": 0, "incomplete": 1}
    assert data["tasks"][0]["name"].endswith("noop.py@noop")
    assert not list(Path(tmp_path / "logs").glob("*.eval"))


def test_run_json_requires_dry_run(tmp_path: Path) -> None:
    spec_file = _write_spec(tmp_path, str(tmp_path / "logs"))
    result = CliRunner().invoke(run_command, [spec_file, "--json"])
    assert result.exit_code != 0
    assert "--json is only supported with --dry-run" in result.output


def test_store_info_json(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(store_command, ["import", _STORE_LOG_DIR, "--log-level", "error"])
    data = _invoke_json(store_command, ["info", "--json"])
    assert data["logs"] == 2
    assert data["log_dirs"] == 1
    assert data["version"] == "0.2.0"
    assert data["path"]


def test_store_info_json_empty() -> None:
    data = _invoke_json(store_command, ["info", "--json"])
    assert data is None


def test_store_list_json(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(store_command, ["import", _STORE_LOG_DIR, "--log-level", "error"])
    data = _invoke_json(store_command, ["list", "--json"])
    assert len(data["logs"]) == 2
    assert all(log.endswith(".eval") for log in data["logs"])
    assert data["logs"] == sorted(data["logs"])


def test_list_log_json() -> None:
    data = _invoke_json(list_command, ["log", _STORE_LOG_DIR, "--json", "--no-page"])
    assert len(data["logs"]) == 2
    log = data["logs"][0]
    assert log["task"] == "inspect_evals/gpqa_diamond"
    assert log["status"] == "success"
    assert log["samples"] == log["total_samples"]
    assert log["log_file"].endswith(".eval")
