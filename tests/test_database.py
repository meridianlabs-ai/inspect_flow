from inspect_flow._database.database import create_database
from inspect_flow._database.deltalake import DeltaLakeDatabase
from inspect_flow._types.flow_types import FlowSpec


def test_store_defaults() -> None:
    spec = FlowSpec()
    database = create_database(spec, base_dir=".")
    assert database
    assert isinstance(database, DeltaLakeDatabase)
    assert database._database_path.stem == "test_store"

    spec = FlowSpec(store="auto")
    database = create_database(spec, base_dir=".")
    assert database
    assert isinstance(database, DeltaLakeDatabase)
    assert database._database_path.stem == "test_store"

    spec = FlowSpec(store=None)
    database = create_database(spec, base_dir=".")
    assert database is None
