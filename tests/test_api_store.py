import shutil
from pathlib import Path

import pytest
from botocore.client import BaseClient
from inspect_flow._util.path_util import path_str
from inspect_flow.api import FlowStore, store_get

parent = str(Path.cwd() / "tests/test_logs")
dir1base = str(Path.cwd() / "tests/test_logs/logs1")
dir2base = str(Path.cwd() / "tests/test_logs/logs2")
dir1 = "file://" + dir1base
dir2 = "file://" + dir2base
log1_name = "2025-12-11T18-00-43+00-00_gpqa-diamond_NL3aygdanSgqAJfzoMFuH6.eval"
log1_path = dir1base + "/" + log1_name


def test_store_get(capsys: pytest.CaptureFixture[str]) -> None:
    store: FlowStore = store_get()
    store.import_log_path(dir1)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir1)} with 2 logs" in captured
    store.import_log_path(dir2)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir2)} with 1 logs" in captured
    store.import_log_path(dir1)
    captured = capsys.readouterr().out
    assert f"Found {path_str(dir1)} with 2 logs" in captured


def test_store_import_recursive() -> None:
    store: FlowStore = store_get()
    assert len(store.get_logs()) == 0
    store.import_log_path(parent, recursive=True)
    assert len(store.get_logs()) == 4


def test_store_import_add_recursive() -> None:
    store: FlowStore = store_get()
    assert len(store.get_logs()) == 0
    store.import_log_path(dir2, recursive=False)
    logs = store.get_logs()
    assert len(logs) == 1
    store.remove_log_path(list(logs))
    assert len(store.get_logs()) == 0

    store.import_log_path(dir2, recursive=True)
    logs = store.get_logs()
    assert len(logs) == 2
    store.remove_log_path(list(logs))
    logs = store.get_logs()
    assert len(logs) == 0


def test_store_remove() -> None:
    store: FlowStore = store_get()
    store.import_log_path(dir1)
    assert len(store.get_logs()) == 2
    store.remove_log_path(dir1)
    assert len(store.get_logs()) == 0


def test_store_remove_escaping(mock_s3: BaseClient) -> None:
    dir = "s3://test-bucket/user's logs"
    log_name = "2025-12-11T18-00-43+00-00_gpqa-diamond_NL3aygdanSgqAJfzoMFuH6.eval"
    local_path = dir1base + "/" + log_name
    mock_s3.upload_file(local_path, "test-bucket", "user's logs/" + log_name)

    store: FlowStore = store_get()
    store.import_log_path(dir)
    store.remove_log_path(dir)
    assert len(store.get_logs()) == 0


def test_local_log_remote_store(mock_s3: BaseClient) -> None:
    store: FlowStore = store_get(store="s3://test-bucket/test-store")
    try:
        store.import_log_path(dir1)
    except ValueError as e:
        assert "Local log directories cannot be added to remote stores." in str(e)
        # 374 Ensure default store subdir is not in the error
        assert "flow_store" not in str(e)


def test_refresh_removes(tmp_path: Path) -> None:
    store: FlowStore = store_get()
    dir1 = tmp_path / "logs1"
    dir1.mkdir()
    shutil.copy(log1_path, dir1)
    dir2 = tmp_path / "logs2"
    dir2.mkdir()
    shutil.copy(log1_path, dir2)

    store.import_log_path(str(dir1 / log1_name))
    store.import_log_path(str(dir2))
    assert len(store.get_logs()) == 2

    shutil.rmtree(dir1)
    shutil.rmtree(dir2)
    store.remove_log_path([], missing=True)
    assert len(store.get_logs()) == 0
