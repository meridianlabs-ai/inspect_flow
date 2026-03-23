from unittest.mock import patch

from click.testing import CliRunner
from inspect_flow._cli.store import store_command
from rich.console import Console

LOG_DIR = "tests/test_logs/logs1"


def _import_logs(runner: CliRunner) -> None:
    runner.invoke(store_command, ["import", LOG_DIR])


def test_arguments_help_command_format_help() -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["import", "--help"])
    assert result.exit_code == 0
    assert "Arguments" in result.output
    assert "PATH..." in result.output


def test_store_import_shows_progress(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["import", LOG_DIR], catch_exceptions=False)

    assert result.exit_code == 0
    captured = recording_console.export_text()

    assert "Reading logs" in captured
    assert "2/2" in captured
    assert "gpqa-diamond" in captured
    assert "Imported 2 new logs" in captured


def test_store_import_dry_run(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(
        store_command, ["import", LOG_DIR, "--dry-run"], catch_exceptions=False
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "DRY RUN" in captured


def test_store_import_store_not_found(recording_console: Console) -> None:
    runner = CliRunner()
    with patch("inspect_flow._cli.store.store_factory", return_value=None):
        result = runner.invoke(
            store_command, ["import", LOG_DIR], catch_exceptions=False
        )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "Store not found" in captured


def test_store_import_copy_from() -> None:
    runner = CliRunner()
    with patch("inspect_flow._cli.store.copy_all_logs") as mock_copy:
        result = runner.invoke(
            store_command,
            ["import", "tests/test_logs/logs1", "--copy-from", LOG_DIR],
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    mock_copy.assert_called_once_with(
        src_dir=LOG_DIR,
        dest_dir="tests/test_logs/logs1",
        dry_run=False,
        recursive=True,
    )


def test_store_import_copy_from_multiple_paths_errors() -> None:
    runner = CliRunner()
    result = runner.invoke(
        store_command, ["import", "path1", "path2", "--copy-from", LOG_DIR]
    )
    assert result.exit_code != 0
    assert "exactly one PATH" in result.output


def test_store_remove_missing_shows_progress(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)

    with patch("inspect_flow._store.deltalake.exists", return_value=False):
        result = runner.invoke(
            store_command,
            ["remove", "--missing", "--dry-run"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    captured = recording_console.export_text()

    assert "Scanning for missing logs" in captured
    assert "2/2" in captured
    assert "gpqa-diamond" in captured
    assert "Removed 2 logs" in captured


def test_store_remove_no_prefix_no_missing_errors() -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["remove"])
    assert result.exit_code != 0
    assert "Either prefix or --missing" in result.output


def test_store_remove_prefix_and_missing_errors() -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["remove", "some_prefix", "--missing"])
    assert result.exit_code != 0
    assert "Cannot specify both" in result.output


def test_store_list_flat(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(store_command, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "gpqa-diamond" in captured
    # Flat format shows full paths with separators
    assert "/" in captured
    assert "├" not in captured


def test_store_list_tree(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(
        store_command, ["list", "--format", "tree"], catch_exceptions=False
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "gpqa-diamond" in captured
    # Tree format uses Rich tree characters
    assert "├" in captured or "└" in captured


def test_store_list_empty(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    runner.invoke(store_command, ["remove", "tests/"])
    result = runner.invoke(store_command, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs in store" in captured


def test_store_info(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(store_command, ["info"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "Path:" in captured
    assert "2 logs" in captured
    assert "Version:" in captured


def test_store_delete(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(store_command, ["delete", "--yes"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "Deleted store" in captured


def test_store_delete_not_found(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["delete", "--yes"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "Store not found" in captured


def test_store_import_path_with_dotdot_is_normalized() -> None:
    # Importing with a path containing ".." should store normalized (absolute) paths,
    # not paths with ".." in them.
    from inspect_flow._store.store import store_factory

    runner = CliRunner()
    path_with_dotdot = "tests/test_logs/logs2/../logs1"
    result = runner.invoke(
        store_command, ["import", path_with_dotdot], catch_exceptions=False
    )
    assert result.exit_code == 0

    store = store_factory("auto", base_dir=".")
    assert store is not None
    logs = store.get_logs()
    assert logs, "Expected logs to be imported"
    dotdot_logs = [log for log in logs if ".." in log]
    assert not dotdot_logs, f"Some log paths contain '..': {dotdot_logs}"
