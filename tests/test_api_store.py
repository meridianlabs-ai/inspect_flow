from pathlib import Path

from inspect_ai._util.file import to_uri
from inspect_flow._util.path_util import path_str
from inspect_flow.api import FlowStore, store_get

parent = str(Path.cwd() / "tests/test_logs")
dir1base = str(Path.cwd() / "tests/test_logs/logs1")
dir2base = str(Path.cwd() / "tests/test_logs/logs2")
dir1 = "file://" + dir1base
dir2 = "file://" + dir2base


def test_store_get(capsys) -> None:
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.import_log_path(dir1)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir1)} with 2 logs" in captured
    assert f"Adding new log directory: {path_str(dir1)}" in captured
    assert store.get_log_dirs() == {dir1}
    store.import_log_path(dir2)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir2)} with 1 logs" in captured
    assert f"Adding new log directory: {path_str(dir2)}" in captured
    assert store.get_log_dirs() == {dir1, dir2}
    store.import_log_path(dir1)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir1)} with 2 logs" in captured
    assert "No new log directories to add" in captured
    assert store.get_log_dirs() == {dir1, dir2}


def test_store_import_recursive() -> None:
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.import_log_path(parent, recursive=True)
    assert sorted(store.get_log_dirs()) == [to_uri(parent)]
    assert len(store.get_logs()) == 4


def test_store_import_add_recursive() -> None:
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.import_log_path(dir2, recursive=False)
    assert sorted(store.get_log_dirs()) == [dir2]
    assert len(store.get_logs()) == 1
    store.import_log_path(dir2, recursive=True)
    assert sorted(store.get_log_dirs()) == [dir2]
    assert len(store.get_logs()) == 2


def test_store_remove() -> None:
    store: FlowStore = store_get()
    store.import_log_path(dir1)
    store.remove_log_path(dir1)
    assert store.get_log_dirs() == set()


def test_store_remove_escaping(mock_s3) -> None:
    dir = "s3://test-bucket/user's logs"
    log_name = "2025-12-11T18-00-43+00-00_gpqa-diamond_NL3aygdanSgqAJfzoMFuH6.eval"
    local_path = dir1base + "/" + log_name
    mock_s3.upload_file(local_path, "test-bucket", "user's logs/" + log_name)

    store: FlowStore = store_get()
    store.import_log_path(dir)
    store.remove_log_path(dir)
    assert store.get_log_dirs() == set()


def test_local_log_remote_store(mock_s3) -> None:
    store: FlowStore = store_get(store="s3://test-bucket/test-store")
    try:
        store.import_log_path(dir1)
    except ValueError as e:
        assert "Local log directories cannot be added to remote stores." in str(e)
        # 374 Ensure default store subdir is not in the error
        assert "flow_store" not in str(e)
