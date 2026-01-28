import json

from inspect_flow._store.deltalake import (
    LOGS,
    TABLES,
    DeltaLakeStore,
    _create_table_description,
)
from semver import Version


def test_version_maintained(tmp_path) -> None:
    """Test that opening a table with a higher patch version maintains that version."""
    store_path = str(tmp_path)
    # Create a table with a higher patch version
    table_def = TABLES[1]
    assert table_def.name == LOGS
    old_version = table_def.version
    new_version = str(Version.parse(old_version).bump_patch())
    table_def.version = new_version
    DeltaLakeStore(store_path=store_path)

    def check_version(store, version) -> None:
        table_path = store._table_path(table_def.name)
        dt = store._get_table(table_path)
        assert dt
        description = dt.metadata().description
        parsed = json.loads(description)
        assert parsed.get("version") == version

    # Restore the old version and open the store
    table_def.version = old_version
    store = DeltaLakeStore(store_path=store_path)
    check_version(store, new_version)
    store.import_log_dir("tests/test_logs/logs1")
    check_version(store, new_version)
    store = DeltaLakeStore(store_path=store_path)
    check_version(store, new_version)

    # test that we can change the table description
    table_path = store._table_path(table_def.name)
    metadata = _create_table_description(table_def)
    dt = store._get_table(table_path)
    assert dt
    dt.alter.set_table_description(metadata)
    store = DeltaLakeStore(store_path=store_path)
    check_version(store, old_version)
