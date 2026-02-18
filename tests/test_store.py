from unittest.mock import MagicMock, call, patch

from inspect_ai.log._file import EvalLogInfo
from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import _flow_store_path, store_factory
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.logs import copy_all_logs


def test_store_defaults() -> None:
    spec = FlowSpec()
    store = store_factory(spec, base_dir=".", create=True)
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert store._store_path.endswith("test_store/flow_store")

    spec = FlowSpec(store="auto")
    store = store_factory(spec, base_dir=".")
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert store._store_path.endswith("test_store/flow_store")

    spec = FlowSpec(store=None)
    store = store_factory(spec, base_dir=".")
    assert store is None


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
