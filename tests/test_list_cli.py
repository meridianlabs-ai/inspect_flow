import shutil
from pathlib import Path

import yaml
from click.testing import CliRunner
from inspect_flow._cli.list import list_command
from inspect_flow._cli.store import store_command
from inspect_flow._steps.tag import tag
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
    assert "Task:" in result.output
    assert "Status:" in result.output
    assert "Samples:" in result.output
    assert "Duration:" in result.output


def test_list_log_oneline(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(list_command, ["log", "--oneline"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "gpqa_diamond" in result.output
    assert "Task:" not in result.output


def test_list_log_empty_store(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    runner.invoke(store_command, ["remove", "tests/"])
    result = runner.invoke(list_command, ["log"], catch_exceptions=False)
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs found" in captured


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
    assert "No logs found" in captured


def test_list_log_no_matches(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(
        list_command,
        ["log", LOG_DIR, "--task", "does-not-exist"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs found" in captured


def test_list_log_paged_no_matches(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(
        list_command,
        ["log", LOG_DIR, "--task", "does-not-exist"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs found" in captured


def test_list_log_tree_no_matches(recording_console: Console) -> None:
    runner = CliRunner()
    result = runner.invoke(
        list_command,
        ["log", LOG_DIR, "--task", "does-not-exist", "--format", "tree"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs found" in captured


_SAMPLE_LOG = "tests/test_logs/logs1/2026-01-09T18-27-59+00-00_gpqa-diamond_nbjF337MtumE8dao4wZ3vj.eval"
_SAMPLE_LOG_FILENAME = _SAMPLE_LOG.rsplit("/", 1)[-1]


def _write_flow_yaml(log_dir: Path, content: dict[str, object]) -> None:
    (log_dir / "flow.yaml").write_text(yaml.dump(content))


def test_list_log_viewer_url_embed_viewer(tmp_path: Path) -> None:
    shutil.copy(_SAMPLE_LOG, tmp_path)
    _write_flow_yaml(
        tmp_path,
        {
            "log_dir": str(tmp_path),
            "options": {
                "bundle_url_mappings": {str(tmp_path): "https://example.com/logs"},
                "embed_viewer": True,
            },
        },
    )
    result = CliRunner().invoke(
        list_command, ["log", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert f"https://example.com/logs/#/logs/{_SAMPLE_LOG_FILENAME}" in result.output


def test_list_log_viewer_url_bundle_dir(tmp_path: Path) -> None:
    shutil.copy(_SAMPLE_LOG, tmp_path)
    bundle_dir = str(tmp_path / "bundle")
    _write_flow_yaml(
        tmp_path,
        {
            "log_dir": str(tmp_path),
            "options": {
                "bundle_dir": bundle_dir,
                "bundle_url_mappings": {bundle_dir: "https://example.com/bundle"},
            },
        },
    )
    result = CliRunner().invoke(
        list_command, ["log", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert f"https://example.com/bundle/#/logs/{_SAMPLE_LOG_FILENAME}" in result.output


def _create_tagged_logs(tmp_path: Path) -> None:
    """Create two logs: one tagged ['golden', 'v2'], one tagged ['draft']."""
    for name, tags in [("log1", ["golden", "v2"]), ("log2", ["draft"])]:
        dest = str(tmp_path / f"{name}.eval")
        shutil.copy(_SAMPLE_LOG, dest)
        tag(dest, add=tags)


def test_list_log_tag_filter(tmp_path: Path) -> None:
    _create_tagged_logs(tmp_path)
    result = CliRunner().invoke(
        list_command, ["log", str(tmp_path), "--tag", "golden"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "log1" in result.output
    assert "log2" not in result.output


def test_list_log_tag_filter_multiple(tmp_path: Path) -> None:
    """Multiple --tag flags use OR: matches logs with any of the tags."""
    _create_tagged_logs(tmp_path)
    result = CliRunner().invoke(
        list_command,
        ["log", str(tmp_path), "--tag", "golden", "--tag", "draft"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "log1" in result.output
    assert "log2" in result.output


def test_list_log_tag_filter_glob(tmp_path: Path) -> None:
    """Tag patterns support glob matching."""
    _create_tagged_logs(tmp_path)
    result = CliRunner().invoke(
        list_command, ["log", str(tmp_path), "--tag", "v*"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "log1" in result.output
    assert "log2" not in result.output


def test_list_log_tag_filter_no_match(
    tmp_path: Path, recording_console: Console
) -> None:
    _create_tagged_logs(tmp_path)
    result = CliRunner().invoke(
        list_command,
        ["log", str(tmp_path), "--tag", "nonexistent"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    assert "No logs found" in captured
