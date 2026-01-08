import json
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Sequence

import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from inspect_ai._eval.evalset import Log, list_all_eval_logs
from inspect_ai._util.file import filesystem
from inspect_ai.log import read_eval_log
from semver import Version

from inspect_flow._store.store import FlowStoreInternal, is_better_log
from inspect_flow._util.constants import PKG_NAME

logger = getLogger(__name__)

TASK_IDENTIFIER_VERSION = 1  # TODO:ransom move to inspect_ai


@dataclass
class TableDef:
    name: str
    version: str
    schema: pa.Schema


LOG_DIRS = "log_dirs"
LOG_DIRS_SCHEMA = pa.schema([("log_dir", pa.string())])

LOGS = "logs"
LOGS_SCHEMA = pa.schema(
    [
        ("task_identifier", pa.string()),
        ("log_path", pa.string()),
    ]
)

TABLES: list[TableDef] = [
    TableDef(
        name=LOG_DIRS,
        version="0.1",
        schema=LOG_DIRS_SCHEMA,
    ),
    TableDef(
        name=LOGS,
        version="0.1",
        schema=LOGS_SCHEMA,
    ),
]


def _create_table_description(table: TableDef) -> str:
    description = {"name": table.name, "version": table.version}
    if table.name == LOGS:
        description["task_identifier_version"] = str(TASK_IDENTIFIER_VERSION)
    return json.dumps(description)


def _check_table_description(table: TableDef, description: str) -> None:
    parsed = json.loads(description)
    if parsed.get("name") != table.name:
        raise ValueError(
            f"Table name mismatch: expected {table.name}, got {parsed.get('name')}"
        )
    if parsed.get("version") != table.version:
        stored = Version.parse(parsed.get("version"))
        code = Version.parse(table.version)
        if stored > code:
            raise ValueError(
                f"Table {table.name} version mismatch: supported {table.version}, got {parsed.get('version')}. {PKG_NAME} upgrade required."
            )
        else:
            raise ValueError(
                f"Table {table.name} version mismatch: supported {table.version}, got {parsed.get('version')}. Store upgrade required."
            )
    if table.name == LOGS:
        if parsed.get("task_identifier_version") != str(TASK_IDENTIFIER_VERSION):
            raise ValueError(
                f"Table {table.name} task identifier version mismatch: expected {TASK_IDENTIFIER_VERSION}, got {parsed.get('task_identifier_version')}. Store update required."
            )


def _add_log_dir(
    log_dir: str, recursive: bool, dirs: set[str], logs: list[Log]
) -> None:
    dir_logs = list_all_eval_logs(log_dir=log_dir)
    if dir_logs or not recursive:
        dirs.add(log_dir)
        logs.extend(dir_logs)

    if recursive:
        fs = filesystem(log_dir)
        file_infos = fs.ls(log_dir)
        for file_info in file_infos:
            if file_info.type == "directory":
                _add_log_dir(
                    log_dir=file_info.name,
                    recursive=recursive,
                    dirs=dirs,
                    logs=logs,
                )


class DeltaLakeStore(FlowStoreInternal):
    """Delta Lake implementation of FlowStore.

    Stores log directory paths in a Delta Lake table for scalable,
    concurrent-safe storage with S3 compatibility.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        for table in TABLES:
            self._init_table(table)

    def _init_table(self, table: TableDef) -> None:
        table_path = str(self._database_path / table.name)
        if self._table_exists(table_path):
            logger.info(f"Existing table: {table_path}")
            dt = DeltaTable(str(table_path))
            _check_table_description(table, dt.metadata().description)
        else:
            logger.info(f"Creating table: {table_path}")
            metadata = _create_table_description(table)
            empty_table = pa.Table.from_pylist([], schema=table.schema)
            write_deltalake(
                table_path,
                empty_table,
                description=metadata,
            )

    def _table_exists(self, table_path: str) -> bool:
        try:
            DeltaTable(table_path)
            return True
        except TableNotFoundError:
            return False

    def add_log_dir(
        self, log_dir: str | Sequence[str], recursive: bool = False
    ) -> None:
        if isinstance(log_dir, str):
            log_dir = [log_dir]
        dirs = set()
        logs = []
        for dir in log_dir:
            _add_log_dir(log_dir=dir, recursive=recursive, dirs=dirs, logs=logs)
        existing_dirs = self.get_log_dirs()
        new_dirs = dirs - existing_dirs
        if new_dirs:
            new_data = pa.Table.from_pylist(
                [{"log_dir": log_dir} for log_dir in new_dirs],
                schema=LOG_DIRS_SCHEMA,
            )

            write_deltalake(
                str(self._database_path / LOG_DIRS),
                new_data,
                mode="append",
            )

        if logs:
            self._add_logs(logs)

    def _add_logs(self, logs: list[Log]) -> None:
        task_ids = {log.task_identifier for log in logs}
        existing_logs = self._get_logs(task_ids)
        new_logs = [
            log
            for log in logs
            if log.info.name not in existing_logs.get(log.task_identifier, set())
        ]
        if not new_logs:
            return

        new_data = pa.Table.from_pylist(
            [
                {"task_identifier": log.task_identifier, "log_path": log.info.name}
                for log in new_logs
            ],
            schema=LOGS_SCHEMA,
        )

        write_deltalake(
            str(self._database_path / LOGS),
            new_data,
            mode="append",
        )

    def search_for_logs(self, task_ids: set[str]) -> list[str]:
        results = []
        remaining_task_ids = set(task_ids)

        indexed_logs = self._get_logs(remaining_task_ids)
        for task_id in list(remaining_task_ids):
            if task_id not in indexed_logs:
                continue
            logs = indexed_logs[task_id]
            best_log = None
            best_eval_log = None
            for log in logs:
                try:
                    eval_log = read_eval_log(log, header_only=True)
                except Exception as e:
                    logger.error(
                        f"Failed to read log {log} referenced from the store. This could be a permissions issue. If expected, use 'flow store remove' to update the store. {e}"
                    )
                    raise
                if is_better_log(eval_log, best_eval_log):
                    best_log = log
                    best_eval_log = eval_log
            if best_log:
                results.append(best_log)
        return results

    def get_log_dirs(self) -> set[str]:
        dt = DeltaTable(str(self._database_path / LOG_DIRS))
        table = dt.to_pyarrow_table()
        return set(table["log_dir"].to_pylist())

    def _get_logs(self, task_ids: set[str]) -> dict[str, set[str]]:
        dt = DeltaTable(str(self._database_path / LOGS))
        dataset = dt.to_pyarrow_dataset()
        table = dataset.to_table(filter=pc.field("task_identifier").isin(task_ids))

        result: dict[str, set[str]] = {}
        for task_id, log_path in zip(
            table["task_identifier"].to_pylist(),
            table["log_path"].to_pylist(),
            strict=True,
        ):
            if task_id not in result:
                result[task_id] = set()
            result[task_id].add(log_path)
        return result
