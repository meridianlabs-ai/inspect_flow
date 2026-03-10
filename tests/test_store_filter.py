from pathlib import Path

import pytest
from click.testing import CliRunner
from inspect_ai._eval.evalset import task_identifier
from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log, write_eval_log
from inspect_flow import FlowOptions, FlowSpec, FlowStoreConfig, FlowTask, log_filter
from inspect_flow._cli.store import store_command
from inspect_flow._runner.run import run_eval_set
from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import store_factory
from inspect_flow._types.log_filter import resolve_log_filter
from rich.console import Console

task_file = "tests/local_eval/src/local_eval/noop.py"


def _run_task(log_dir: str, limit: int | None = None) -> str:
    options = FlowOptions(limit=limit) if limit else FlowOptions()
    spec = FlowSpec(
        log_dir=log_dir,
        store=None,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
        options=options,
    )
    run_eval_set(spec=spec, base_dir=".")
    logs = list_eval_logs(log_dir)
    assert len(logs) == 1
    return str(logs[0].name)


# -- Registry tests --


@log_filter
def success_only(log: EvalLog) -> bool:
    return log.status == "success"


@log_filter
def has_tag_golden(log: EvalLog) -> bool:
    return "golden" in (log.eval.tags or [])


def test_resolve_log_filter_callable() -> None:
    fn = lambda log: log.status == "success"  # noqa: E731
    assert resolve_log_filter(fn) is fn


def test_resolve_log_filter_none() -> None:
    assert resolve_log_filter(None) is None


def test_resolve_log_filter_registered_name() -> None:
    resolved = resolve_log_filter("success_only")
    assert resolved is success_only


def test_resolve_log_filter_unknown_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        resolve_log_filter("nonexistent_filter")


# -- FlowStoreConfig tests --


def test_store_config_in_store_factory(tmp_path: Path) -> None:
    store_dir = str(tmp_path / "store")
    config = FlowStoreConfig(path=store_dir)
    spec = FlowSpec(store=config)
    store = store_factory(spec, base_dir=".", create=True)
    assert store is not None
    assert isinstance(store, DeltaLakeStore)


def test_store_config_none_path_disables() -> None:
    config = FlowStoreConfig(path=None)
    spec = FlowSpec(store=config)
    store = store_factory(spec, base_dir=".")
    assert store is None


def test_store_config_with_filter(tmp_path: Path) -> None:
    store_dir = str(tmp_path / "store")
    config = FlowStoreConfig(path=store_dir, filter=success_only)
    spec = FlowSpec(store=config)
    store = store_factory(spec, base_dir=".", create=True)
    assert store is not None
    assert isinstance(store, DeltaLakeStore)
    assert store._log_filter is success_only


def test_store_config_with_string_filter(tmp_path: Path) -> None:
    store_dir = str(tmp_path / "store")
    config = FlowStoreConfig(path=store_dir, filter="success_only")
    spec = FlowSpec(store=config)
    store = store_factory(spec, base_dir=".", create=True)
    assert store is not None
    assert isinstance(store, DeltaLakeStore)
    assert store._log_filter is success_only


# -- search_for_logs filter tests --


def test_search_for_logs_filter_excludes(tmp_path: Path) -> None:
    """search_for_logs skips logs that fail the store filter."""
    log_dir = str(tmp_path / "logs")
    log_path = _run_task(log_dir)

    # Mark the log as error status
    log = read_eval_log(log_path)
    log.status = "error"
    write_eval_log(log, log_path)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(
        store_path=store_dir, create=True, quiet=True, log_filter=success_only
    )
    store.import_log_path(log_dir)

    task_id = task_identifier(read_eval_log(log_path, header_only=True), None)
    results = store.search_for_logs({task_id})
    assert len(results) == 0


def test_search_for_logs_filter_includes(tmp_path: Path) -> None:
    """search_for_logs includes logs that pass the store filter."""
    log_dir = str(tmp_path / "logs")
    log_path = _run_task(log_dir)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(
        store_path=store_dir, create=True, quiet=True, log_filter=success_only
    )
    store.import_log_path(log_dir)

    task_id = task_identifier(read_eval_log(log_path, header_only=True), None)
    results = store.search_for_logs({task_id})
    assert len(results) == 1


def test_search_for_logs_no_filter(tmp_path: Path) -> None:
    """Without a filter, search_for_logs returns all matching logs."""
    log_dir = str(tmp_path / "logs")
    log_path = _run_task(log_dir)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path(log_dir)

    task_id = task_identifier(read_eval_log(log_path, header_only=True), None)
    results = store.search_for_logs({task_id})
    assert len(results) == 1


# -- get_logs filter tests --


def test_get_logs_with_filter(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    log_path = _run_task(log_dir)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path(log_dir)

    # success_only should include
    assert len(store.get_logs(filter=success_only)) == 1

    # Mark log as error
    log = read_eval_log(log_path)
    log.status = "error"
    write_eval_log(log, log_path)

    assert len(store.get_logs(filter=success_only)) == 0


def test_get_logs_filter_conflict_raises(tmp_path: Path) -> None:
    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(
        store_path=store_dir, create=True, quiet=True, log_filter=success_only
    )
    with pytest.raises(ValueError, match="per-call filter"):
        store.get_logs(filter=has_tag_golden)


# -- remove_log_prefix filter tests --


def test_remove_log_prefix_with_filter(
    tmp_path: Path, recording_console: Console
) -> None:
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    log1 = _run_task(log_dir1)
    log2 = _run_task(log_dir2)

    # Mark log2 as error
    log = read_eval_log(log2)
    log.status = "error"
    write_eval_log(log, log2)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path([log_dir1, log_dir2])
    assert len(store.get_logs()) == 2

    # Remove only error logs
    error_filter = lambda log: log.status == "error"  # noqa: E731
    store.remove_log_prefix([str(tmp_path)], recursive=True, filter=error_filter)
    assert len(store.get_logs()) == 1

    # The remaining log should be the successful one
    remaining = store.get_logs()
    assert log1 in remaining


# -- CLI filter/exclude tests --


LOG_DIR = "tests/test_logs/logs1"


def _import_logs(runner: CliRunner) -> None:
    runner.invoke(store_command, ["import", LOG_DIR])


def test_store_list_filter_and_exclude_mutually_exclusive() -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(
        store_command, ["list", "--filter", "success_only", "--exclude", "success_only"]
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_store_remove_filter_and_exclude_mutually_exclusive() -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(
        store_command,
        ["remove", "tests/", "--filter", "success_only", "--exclude", "success_only"],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_store_list_with_filter(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(
        store_command, ["list", "--filter", "success_only"], catch_exceptions=False
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    # Test logs are successful, so they should appear
    assert "gpqa-diamond" in captured


def test_store_list_with_exclude(recording_console: Console) -> None:
    runner = CliRunner()
    _import_logs(runner)
    result = runner.invoke(
        store_command, ["list", "--exclude", "success_only"], catch_exceptions=False
    )
    assert result.exit_code == 0
    captured = recording_console.export_text()
    # Test logs are successful, so excluding success_only should show nothing
    assert "No logs in store" in captured


# -- FlowSpec.store backwards compatibility --


def test_store_field_accepts_string() -> None:
    spec = FlowSpec(store="auto")
    assert spec.store == "auto"


def test_store_field_accepts_none() -> None:
    spec = FlowSpec(store=None)
    assert spec.store is None


def test_store_field_accepts_config() -> None:
    config = FlowStoreConfig(path="./my-store", filter="success_only")
    spec = FlowSpec(store=config)
    assert isinstance(spec.store, FlowStoreConfig)
    assert spec.store.path == "./my-store"
    assert spec.store.filter == "success_only"
