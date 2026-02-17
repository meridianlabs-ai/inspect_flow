from unittest.mock import patch

from click.testing import CliRunner
from inspect_flow._cli.store import store_command
from rich.console import Console

LOG_DIR = "tests/test_logs/logs1"


def test_store_import_shows_progress(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(
        store_command,
        ["import", LOG_DIR, "--log-level", "error"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    captured = recording_console.export_text()

    # Progress bar was shown and advanced to completion
    assert "Reading logs" in captured
    assert "2/2" in captured

    # Footer showed the log paths
    assert "gpqa-diamond" in captured

    # Import message
    assert "Imported 2 new logs" in captured


def test_store_remove_missing_shows_progress(recording_console: Console) -> None:
    runner = CliRunner()
    runner.invoke(store_command, ["import", LOG_DIR, "--log-level", "error"])

    with patch("inspect_flow._store.deltalake.exists", return_value=False):
        result = runner.invoke(
            store_command,
            ["remove", "--missing", "--dry-run", "--log-level", "error"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    captured = recording_console.export_text()

    # Progress bar was shown and advanced to completion
    assert "Scanning for missing logs" in captured
    assert "2/2" in captured

    # Footer showed the log paths
    assert "gpqa-diamond" in captured

    # Dry-run removal message
    assert "Removed 2 logs" in captured
