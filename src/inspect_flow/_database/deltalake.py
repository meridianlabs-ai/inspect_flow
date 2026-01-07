import json
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from inspect_ai._eval.evalset import Log, list_all_eval_logs
from inspect_ai.log import read_eval_log
from semver import Version

from inspect_flow._database.database import FlowDatabase, is_better_log
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


class DeltaLakeDatabase(FlowDatabase):
    """Delta Lake implementation of FlowDatabase.

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

    def add_log_dir(self, log_dir: str) -> None:
        existing_dirs = self._get_log_dirs()
        if log_dir not in existing_dirs:
            new_data = pa.Table.from_pydict(
                {"log_dir": [log_dir]},
                schema=LOG_DIRS_SCHEMA,
            )

            write_deltalake(
                str(self._database_path / LOG_DIRS),
                new_data,
                mode="append",
            )

        logs = list_all_eval_logs(log_dir=log_dir)
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

    def _get_log_dirs(self) -> set[str]:
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
