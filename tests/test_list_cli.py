from click.testing import CliRunner
from inspect_flow._cli.list import list_command
from inspect_flow._cli.store import store_command
from rich.console import Console

LOG_DIR = "tests/test_logs/logs1"


def _import_logs(runner: CliRunner) -> None:
    runner.invoke(store_command, ["import", LOG_DIR])


def test_list_log(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(list_command, ["log"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "gpqa_diamond" in result.output


def test_list_log_empty_store(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    runner.invoke(store_command, ["remove", "tests/"])
    result = runner.invoke(list_command, ["log"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs in store" in captured


def test_list_log_path() -> None:
    runner = CliRunner()
    result = runner.invoke(list_command, ["log", LOG_DIR], catch_exceptions=False)
    assert result.exit_code == 0
    assert "gpqa_diamond" in result.output


def test_list_log_no_store(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(list_command, ["log"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "Store not found" in captured
