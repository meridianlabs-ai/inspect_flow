from pathlib import Path

from inspect_flow._util.path_util import path_str
from inspect_flow.api import FlowStore, store_get

parent = str(Path.cwd() / "tests/test_logs")
dir1 = "file://" + str(Path.cwd() / "tests/test_logs/logs1")
dir2 = "file://" + str(Path.cwd() / "tests/test_logs/logs2")


def test_store_get(capsys) -> None:
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.add_log_dir(dir1)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir1)} with 2 logs" in captured
    assert f"Adding new log directory: {path_str(dir1)}" in captured
    assert store.get_log_dirs() == {dir1}
    store.add_log_dir(dir2)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir2)} with 2 logs" in captured
    assert f"Adding new log directory: {path_str(dir2)}" in captured
    assert store.get_log_dirs() == {dir1, dir2}
    store.add_log_dir(dir1)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir1)} with 2 logs" in captured
    assert "No new log directories to add" in captured
    assert store.get_log_dirs() == {dir1, dir2}


def test_store_add_recursive() -> None:
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.add_log_dir(parent, recursive=True)
    assert sorted(store.get_log_dirs()) == sorted([dir1, dir2])


def test_store_remove() -> None:
    store: FlowStore = store_get()
    store.add_log_dir(dir1)
    store.remove_log_dir(dir1)
    assert store.get_log_dirs() == set()


def test_local_log_remote_store(mock_s3) -> None:
    store: FlowStore = store_get(store="s3://test-bucket/test-store")
    try:
        store.add_log_dir(dir1)
    except ValueError as e:
        assert "Local log directories cannot be added to remote stores." in str(e)
        # 374 Ensure default store subdir is not in the error
        assert "flow_store" not in str(e)
