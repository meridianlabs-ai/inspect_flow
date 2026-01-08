from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import store_factory
from inspect_flow._types.flow_types import FlowSpec


def test_store_defaults() -> None:
    spec = FlowSpec()
    database = store_factory(spec, base_dir=".")
    assert database
    assert isinstance(database, DeltaLakeStore)
    assert database._database_path.stem == "test_store"

    spec = FlowSpec(store="auto")
    database = store_factory(spec, base_dir=".")
    assert database
    assert isinstance(database, DeltaLakeStore)
    assert database._database_path.stem == "test_store"

    spec = FlowSpec(store=None)
    database = store_factory(spec, base_dir=".")
    assert database is None
