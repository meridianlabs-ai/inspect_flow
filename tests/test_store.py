from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import _flow_store_path, store_factory
from inspect_flow._types.flow_types import FlowSpec


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


def test_flow_store_path_trailing_slash() -> None:
    assert _flow_store_path("s3://bucket/store") == "s3://bucket/store/flow_store"
    assert _flow_store_path("s3://bucket/store/") == "s3://bucket/store/flow_store"
