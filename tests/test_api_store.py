from pathlib import Path

from inspect_flow.api import FlowStore, store_get


def test_store_get() -> None:
    dir1 = str(Path.cwd() / "tests/test_logs/logs1")
    dir2 = str(Path.cwd() / "tests/test_logs/logs2")
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.add_log_dir(dir1)
    assert store.get_log_dirs() == {dir1}
    store.add_log_dir(dir2)
    assert store.get_log_dirs() == {dir1, dir2}
    store.add_log_dir(dir1)
    assert store.get_log_dirs() == {dir1, dir2}
