from pathlib import Path

from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import store_factory
from inspect_flow._types.flow_types import FlowSpec


def test_store_defaults() -> None:
    spec = FlowSpec()
    store = store_factory(spec, base_dir=".")
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert Path(store._store_path).stem == "test_store"

    spec = FlowSpec(store="auto")
    store = store_factory(spec, base_dir=".")
    assert store
    assert isinstance(store, DeltaLakeStore)
    assert Path(store._store_path).stem == "test_store"

    spec = FlowSpec(store=None)
    store = store_factory(spec, base_dir=".")
    assert store is None
