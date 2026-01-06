from inspect_flow._database.database import create_database
from inspect_flow._database.database_file import FileDatabase
from inspect_flow._types.flow_types import FlowSpec


def test_cache_defaults() -> None:
    spec = FlowSpec()
    database: FileDatabase | None = create_database(spec, base_dir=".")  # type: ignore
    assert database
    assert database._database_path.parent.stem == "test_cache"

    spec = FlowSpec(cache="auto")
    database = create_database(spec, base_dir=".")  # type: ignore
    assert database
    assert database._database_path.parent.stem == "test_cache"

    spec = FlowSpec(cache=None)
    database = create_database(spec, base_dir=".")  # type: ignore
    assert database is None
