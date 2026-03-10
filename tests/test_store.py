from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from botocore.client import BaseClient
from inspect_ai._eval.evalset import task_identifier
from inspect_ai.log import list_eval_logs, read_eval_log, write_eval_log
from inspect_ai.log._file import EvalLogInfo
from inspect_flow import FlowOptions, FlowSpec, FlowTask
from inspect_flow._runner.run import run_eval_set
from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import _flow_store_path, is_better_log, store_factory
from inspect_flow._util.logs import copy_all_logs
from rich.console import Console

task_file = "tests/local_eval/src/local_eval/noop.py"


def _run_task(log_dir: str, limit: int | None = None) -> str:
    """Run the noop task and return the log file path."""
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


def test_store_defaults() -> None:
    spec = FlowSpec()
    store = store_factory(spec, base_dir=".", create=True)
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert store._store_path.endswith("user_data/flow_store")

    spec = FlowSpec(store="auto")
    store = store_factory(spec, base_dir=".")
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert store._store_path.endswith("user_data/flow_store")

    spec = FlowSpec(store=None)
    store = store_factory(spec, base_dir=".")
    assert store is None


def test_533_store_s3_path_trailing_slash(mock_s3: BaseClient) -> None:
    spec = FlowSpec(store="s3://bucket/store/")
    store = store_factory(spec, base_dir=".", create=True)
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert store._store_path == "s3://bucket/store/flow_store"


def _log_info(name: str) -> EvalLogInfo:
    return EvalLogInfo(
        name=name, type="eval", size=100, mtime=0.0, task="t", task_id="t1", suffix=None
    )


@patch("inspect_flow._util.logs.copy_file")
@patch("inspect_flow._util.logs.list_eval_logs")
def test_copy_all_logs_preserves_tree(
    mock_list: MagicMock, mock_copy: MagicMock
) -> None:
    mock_list.return_value = [
        _log_info("/src/sub1/a.eval"),
        _log_info("/src/sub1/sub2/b.eval"),
        _log_info("/src/c.eval"),
    ]
    copy_all_logs(src_dir="/src", dest_dir="/dest", dry_run=False, recursive=True)

    mock_copy.assert_has_calls(
        [
            call("/src/sub1/a.eval", "/dest/sub1/a.eval"),
            call("/src/sub1/sub2/b.eval", "/dest/sub1/sub2/b.eval"),
            call("/src/c.eval", "/dest/c.eval"),
        ]
    )


@patch("inspect_flow._util.logs.copy_file")
@patch("inspect_flow._util.logs.list_eval_logs")
def test_copy_all_logs_file_protocol(
    mock_list: MagicMock, mock_copy: MagicMock
) -> None:
    mock_list.return_value = [
        _log_info("file:///src/sub1/a.eval"),
        _log_info("file:///src/c.eval"),
    ]
    copy_all_logs(src_dir="/src", dest_dir="/dest", dry_run=False, recursive=True)

    mock_copy.assert_has_calls(
        [
            call("file:///src/sub1/a.eval", "/dest/sub1/a.eval"),
            call("file:///src/c.eval", "/dest/c.eval"),
        ]
    )


@patch("inspect_flow._util.logs.copy_file")
@patch("inspect_flow._util.logs.list_eval_logs")
def test_copy_all_logs_relative_paths(
    mock_list: MagicMock, mock_copy: MagicMock
) -> None:
    mock_list.return_value = [
        _log_info("file:///cwd/logs/sub/a.eval"),
        _log_info("file:///cwd/logs/b.eval"),
    ]
    with patch("inspect_flow._util.logs.absolute_file_path", return_value="/cwd/logs"):
        copy_all_logs(src_dir="logs", dest_dir="dest", dry_run=False, recursive=True)

    mock_copy.assert_has_calls(
        [
            call("file:///cwd/logs/sub/a.eval", "dest/sub/a.eval"),
            call("file:///cwd/logs/b.eval", "dest/b.eval"),
        ]
    )


def test_flow_store_path_trailing_slash() -> None:
    assert _flow_store_path("s3://bucket/store") == "s3://bucket/store/flow_store"
    assert _flow_store_path("s3://bucket/store/") == "s3://bucket/store/flow_store"


def test_is_better_log_all_paths(tmp_path: Path) -> None:
    """Exercise every branch of is_better_log with real logs."""
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    partial_path = _run_task(log_dir1, limit=1)
    full_path = _run_task(log_dir2)

    partial = read_eval_log(partial_path, header_only=True)
    full = read_eval_log(full_path, header_only=True)

    # best is None → always True
    assert is_better_log(partial, None) is True

    # candidate has no results → False
    no_results = full.model_copy()
    no_results.results = None
    assert is_better_log(no_results, partial) is False

    # candidate invalidated → False
    invalidated = full.model_copy()
    invalidated.invalidated = True
    assert is_better_log(invalidated, partial) is False

    # best has no results → True
    assert is_better_log(partial, no_results) is True

    # best invalidated → True
    best_inv = partial.model_copy()
    best_inv.invalidated = True
    assert is_better_log(full, best_inv) is True

    # more completed samples → True
    assert is_better_log(full, partial) is True

    # fewer completed samples → False
    assert is_better_log(partial, full) is False

    # equal samples, more recent → True, older → False
    full2 = full.model_copy(deep=True)
    ts = datetime.fromisoformat(full2.stats.completed_at)
    full2.stats.completed_at = (
        (ts + timedelta(seconds=10)).astimezone(timezone.utc).isoformat()
    )
    assert is_better_log(full2, full) is True
    assert is_better_log(full, full2) is False


def test_search_prefers_more_completed_samples(tmp_path: Path) -> None:
    """search_for_logs returns the log with more completed samples."""
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    # Run with limit=1 (1 completed sample) and then with all samples (2 completed)
    log1 = _run_task(log_dir1, limit=1)
    log2 = _run_task(log_dir2)

    header1 = read_eval_log(log1, header_only=True)
    header2 = read_eval_log(log2, header_only=True)
    assert header1.results and header2.results
    assert header1.results.completed_samples == 1
    assert header2.results.completed_samples == 2

    task_id = task_identifier(header1, None)
    assert task_id == task_identifier(header2, None)

    # Import both into a store and verify search picks the better one
    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path([log_dir1, log_dir2])

    results = store.search_for_logs({task_id})
    assert len(results) == 1
    assert results[task_id] == log2


def test_search_skips_log_without_results(tmp_path: Path) -> None:
    """A log without results loses to a valid log with fewer samples."""
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    log1 = _run_task(log_dir1)
    log2 = _run_task(log_dir2, limit=1)

    # Strip results from log1
    full = read_eval_log(log1)
    full.results = None
    write_eval_log(full, log1)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path([log_dir1, log_dir2])

    task_id = task_identifier(read_eval_log(log2, header_only=True), None)
    results = store.search_for_logs({task_id})
    assert results[task_id] == log2


def test_search_prefers_valid_over_no_results(tmp_path: Path) -> None:
    """A valid candidate replaces a best that has no results."""
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    log1 = _run_task(log_dir1)
    log2 = _run_task(log_dir2, limit=1)

    # Strip results from log2 (may become best first due to iteration order)
    no_results = read_eval_log(log2)
    no_results.results = None
    write_eval_log(no_results, log2)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path([log_dir1, log_dir2])

    task_id = task_identifier(read_eval_log(log1, header_only=True), None)
    results = store.search_for_logs({task_id})
    assert results[task_id] == log1


def test_search_skips_invalidated_log(tmp_path: Path) -> None:
    """An invalidated log with more samples loses to a valid log with fewer samples."""
    log_dir_full = str(tmp_path / "logs_full")
    log_dir_partial = str(tmp_path / "logs_partial")

    log_full = _run_task(log_dir_full)
    log_partial = _run_task(log_dir_partial, limit=1)

    # Invalidate the full log
    full = read_eval_log(log_full)
    assert full.results and full.results.completed_samples == 2
    full.invalidated = True
    write_eval_log(full, log_full)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path([log_dir_full, log_dir_partial])

    task_id = task_identifier(read_eval_log(log_full, header_only=True), None)
    results = store.search_for_logs({task_id})
    # The partial (1 sample) log wins because the full one is invalidated
    assert results[task_id] == log_partial


def test_search_uses_invalidated_log_when_only_option(tmp_path: Path) -> None:
    """An invalidated log is still returned when it's the only log available."""
    log_dir = str(tmp_path / "logs")
    log_path = _run_task(log_dir)

    full = read_eval_log(log_path)
    full.invalidated = True
    write_eval_log(full, log_path)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path(log_dir)

    task_id = task_identifier(read_eval_log(log_path, header_only=True), None)
    results = store.search_for_logs({task_id})
    assert results[task_id] == log_path


def test_search_prefers_more_recent_when_equal_samples(tmp_path: Path) -> None:
    """When completed samples are equal, search_for_logs returns the more recent log."""
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")

    log1 = _run_task(log_dir1)
    log2 = _run_task(log_dir2)

    # Bump log2's completed_at so it's clearly more recent
    log2_full = read_eval_log(log2)
    ts = datetime.fromisoformat(log2_full.stats.completed_at)
    log2_full.stats.completed_at = (
        (ts + timedelta(seconds=10)).astimezone(timezone.utc).isoformat()
    )
    write_eval_log(log2_full, log2)

    header1 = read_eval_log(log1, header_only=True)
    header2 = read_eval_log(log2, header_only=True)
    assert header1.results and header2.results
    assert header1.results.completed_samples == header2.results.completed_samples
    assert header2.stats.completed_at > header1.stats.completed_at

    task_id = task_identifier(header1, None)

    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True, quiet=True)
    store.import_log_path([log_dir1, log_dir2])

    results = store.search_for_logs({task_id})
    assert results[task_id] == log2


def test_search_uses_store_in_run(recording_console: Console, tmp_path: Path) -> None:
    """run_eval_set picks the best log from the store when re-running."""
    log_dir1 = str(tmp_path / "logs1")
    log_dir2 = str(tmp_path / "logs2")
    store_dir = str(tmp_path / "store")

    # First run: limit=1, indexed into store
    spec1 = FlowSpec(
        log_dir=log_dir1,
        store=store_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
        options=FlowOptions(limit=1),
    )
    run_eval_set(spec=spec1, base_dir=".")

    # Second run: full samples, also indexed into store
    spec2 = FlowSpec(
        log_dir=log_dir2,
        store=store_dir,
        tasks=[FlowTask(name=task_file + "@noop", model="mockllm/mock-llm")],
    )
    run_eval_set(spec=spec2, base_dir=".")

    # Both logs should be in the store
    store = DeltaLakeStore(store_path=store_dir, quiet=True)
    assert len(store.get_logs()) == 2

    header = read_eval_log(list_eval_logs(log_dir2)[0].name, header_only=True)
    task_id = task_identifier(header, None)

    # search_for_logs should pick the full-sample log
    results = store.search_for_logs({task_id})
    full_log = str(list_eval_logs(log_dir2)[0].name)
    assert results[task_id] == full_log


def test_copy_all_logs_s3_to_s3(mock_s3: BaseClient) -> None:
    src_dir = "s3://test-bucket/src-logs"
    dest_dir = "s3://test-bucket/dest-logs/"

    _run_task(src_dir)
    src_logs = list_eval_logs(src_dir)
    assert len(src_logs) == 1

    copy_all_logs(src_dir=src_dir, dest_dir=dest_dir, dry_run=False, recursive=True)

    dest_logs = list_eval_logs(dest_dir)
    assert len(dest_logs) == 1

    src_log = read_eval_log(src_logs[0].name)
    dest_log = read_eval_log(dest_logs[0].name)
    assert src_log.status == dest_log.status
    assert src_log.eval.task == dest_log.eval.task
