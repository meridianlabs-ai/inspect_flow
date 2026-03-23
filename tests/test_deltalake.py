import json
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake
from inspect_ai._util.file import to_uri
from inspect_flow._store.deltalake import (
    LOGS,
    TABLES,
    DeltaLakeStore,
    LogRecord,
    TableDef,
    _check_table_description,
    _create_table_description,
    _file_to_log,
    _task_id_col,
)
from semver import Version

parent = str(Path.cwd() / "tests/test_logs")
dir1base = str(Path.cwd() / "tests/test_logs/logs1")
dir2base = str(Path.cwd() / "tests/test_logs/logs2")
dir1 = "file://" + dir1base
dir2 = "file://" + dir2base
log1_name = "2025-12-11T18-00-43+00-00_gpqa-diamond_NL3aygdanSgqAJfzoMFuH6.eval"
log1_path = dir1 + "/" + log1_name


def test_version_maintained(tmp_path: Path) -> None:
    """Test that opening a table with a higher patch version maintains that version."""
    store_path = str(tmp_path)
    # Create a table with a higher patch version
    table_def = TABLES[0]
    assert table_def.name == LOGS
    old_version = table_def.version
    new_version = str(Version.parse(old_version).bump_patch())
    table_def.version = new_version
    DeltaLakeStore(store_path=store_path, create=True)

    def check_version(store: DeltaLakeStore, version: str) -> None:
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
    store.import_log_path("tests/test_logs/logs1")
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


def test_missing_task_identifier(tmp_path: Path) -> None:
    store_path = str(tmp_path)
    store = DeltaLakeStore(store_path=store_path)
    table_def = TABLES[0]
    assert table_def.name == LOGS

    record = LogRecord(
        log_path=to_uri(log1_path),
        task_identifier_1="invalid",
    )
    dict = record.to_dict()
    dict.pop(_task_id_col())  # don't set the task_identifier

    new_data = pa.Table.from_pylist(
        [dict],
        schema=LogRecord.to_schema(),
    )

    write_deltalake(
        store._table_path(LOGS),
        new_data,
        mode="append",
        storage_options=store._storage_options,
    )

    log = _file_to_log(log1_path)

    logs = store.search_for_logs({log.task_identifier})
    assert logs == {log.task_identifier: to_uri(log1_path)}


class TestCheckTableDescription:
    """Tests for _check_table_description version validation."""

    def test_newer_major_version_raises(self) -> None:
        """A stored major version newer than code raises ValueError."""
        table = TABLES[0]
        newer = str(Version.parse(table.version).bump_major())
        desc = json.dumps({"name": table.name, "version": newer})
        with pytest.raises(ValueError, match="upgrade required"):
            _check_table_description(table, desc)

    def test_newer_minor_version_raises(self) -> None:
        """A stored minor version newer than code raises ValueError."""
        table = TABLES[0]
        newer = str(Version.parse(table.version).bump_minor())
        desc = json.dumps({"name": table.name, "version": newer})
        with pytest.raises(ValueError, match="upgrade required"):
            _check_table_description(table, desc)

    def test_newer_patch_version_passes(self) -> None:
        """A stored patch version newer than code is allowed (backward compatible)."""
        table = TABLES[0]
        newer = str(Version.parse(table.version).bump_patch())
        desc = json.dumps({"name": table.name, "version": newer})
        _check_table_description(table, desc)

    def test_older_stored_version_passes(self) -> None:
        """A stored version older than the code version is allowed."""
        table = TABLES[0]
        newer_code = str(Version.parse(table.version).bump_minor())
        desc = json.dumps({"name": table.name, "version": table.version})
        newer_table = TableDef(name=table.name, version=newer_code, schema=table.schema)
        _check_table_description(newer_table, desc)

    def test_name_mismatch_raises(self) -> None:
        table = TABLES[0]
        desc = json.dumps({"name": "wrong_name", "version": table.version})
        with pytest.raises(ValueError, match="Table name mismatch"):
            _check_table_description(table, desc)

    def test_newer_major_on_open_raises(self, tmp_path: Path) -> None:
        """Opening a store whose table has a newer major version raises."""
        table_def = TABLES[0]
        old_version = table_def.version

        # Create store with bumped major version
        table_def.version = str(Version.parse(old_version).bump_major())
        try:
            DeltaLakeStore(store_path=str(tmp_path), create=True)
        finally:
            table_def.version = old_version

        # Opening with current (lower) code version should fail
        with pytest.raises(ValueError, match="upgrade required"):
            DeltaLakeStore(store_path=str(tmp_path))
