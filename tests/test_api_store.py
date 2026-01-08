from inspect_flow.api import FlowStore, store_get


def test_store_get() -> None:
    store: FlowStore = store_get()
    assert store.get_log_dirs() == set()
    store.add_log_dir("logs/run1")
    assert store.get_log_dirs() == {"logs/run1"}
    store.add_log_dir("logs/run2")
    assert store.get_log_dirs() == {"logs/run1", "logs/run2"}
    store.add_log_dir("logs/run1")
    assert store.get_log_dirs() == {"logs/run1", "logs/run2"}
