import json
from logging import getLogger
from pathlib import Path
from typing import Any

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from inspect_ai._eval.evalset import list_all_eval_logs
from inspect_ai.log import read_eval_log

from inspect_flow._database.database import FlowDatabase, is_better_log
from inspect_flow._util.constants import PKG_NAME

logger = getLogger(__name__)

LOG_DIRS_TABLE_VERSION = "0.0.1"
LOG_DIRS_SCHEMA = pa.schema(
    [
        ("log_dir", pa.string()),
    ]
)

LOGS_TABLE_VERSION = "0.0.1"
LOGS_SCHEMA = pa.schema(
    [
        ("task_identifier", pa.string()),
        ("log_path", pa.string()),
    ]
)


def _create_table_metadata(table_name: str, version: str) -> dict[str, Any]:
    """Create metadata dictionary for table description."""
    return {
        "package": PKG_NAME,
        "table": table_name,
        "schema_version": version,
    }


def _parse_table_metadata(description: str | None) -> dict[str, Any] | None:
    """Parse metadata from table description."""
    if not description:
        return None
    try:
        return json.loads(description)
    except json.JSONDecodeError:
        return None


class DeltaLakeDatabase(FlowDatabase):
    """Delta Lake implementation of FlowDatabase.

    Stores log directory paths in a Delta Lake table for scalable,
    concurrent-safe storage with S3 compatibility.
    """

    def __init__(self, database_path: Path) -> None:
        """Initialize the DeltaLakeDatabase.

        Args:
            database_path: Path to the Delta Lake table directory.
        """
        self._database_path = database_path
        self._log_dirs_table_path = str(database_path / "log_dirs")
        self._logs_table_path = str(database_path / "logs")
        if self._log_dirs_table_exists():
            logger.info(f"Existing database: {self._database_path}")
            self._check_log_dirs_version()
        else:
            logger.info(f"Creating database: {self._database_path}")
        if self._logs_table_exists():
            self._check_logs_version()

    def _check_table_version(
        self, table_path: str, expected_version: str, table_name: str
    ) -> None:
        """Check a table's version and log a warning if it doesn't match."""
        dt = DeltaTable(table_path)
        metadata = _parse_table_metadata(dt.metadata().description)
        if metadata is None:
            logger.warning(
                f"Table {table_path} has no schema version metadata. "
                f"Expected version {expected_version}."
            )
            return
        version = metadata.get("schema_version")
        if version is None:
            logger.warning(
                f"Table {table_path} has no schema version. "
                f"Expected {expected_version}."
            )
        elif version != expected_version:
            logger.warning(
                f"Table {table_path} has schema version {version}, "
                f"but expected {expected_version}."
            )

    def _check_log_dirs_version(self) -> None:
        """Check the log_dirs table version."""
        self._check_table_version(
            self._log_dirs_table_path, LOG_DIRS_TABLE_VERSION, "log_dirs"
        )

    def _check_logs_version(self) -> None:
        """Check the logs table version."""
        self._check_table_version(self._logs_table_path, LOGS_TABLE_VERSION, "logs")

    def _table_exists(self, table_path: str) -> bool:
        """Check if a Delta table exists."""
        try:
            DeltaTable(table_path)
            return True
        except TableNotFoundError:
            return False

    def _log_dirs_table_exists(self) -> bool:
        """Check if the log_dirs table exists."""
        return self._table_exists(self._log_dirs_table_path)

    def _logs_table_exists(self) -> bool:
        """Check if the logs table exists."""
        return self._table_exists(self._logs_table_path)

    def add_log_dir(self, log_dir: str) -> None:
        """Add a log directory to the database.

        Args:
            log_dir: Absolute path to the log directory to add.
        """
        existing_dirs = self._get_log_dirs()
        if log_dir in existing_dirs:
            return

        new_data = pa.Table.from_pydict(
            {"log_dir": [log_dir]},
            schema=LOG_DIRS_SCHEMA,
        )

        self._database_path.mkdir(parents=True, exist_ok=True)

        if self._log_dirs_table_exists():
            write_deltalake(
                self._log_dirs_table_path,
                new_data,
                mode="append",
            )
        else:
            metadata = _create_table_metadata("log_dirs", LOG_DIRS_TABLE_VERSION)
            write_deltalake(
                self._log_dirs_table_path,
                new_data,
                description=json.dumps(metadata),
            )

    def add_log(self, task_identifier: str, log_path: str) -> None:
        """Add an individual log record to the database.

        Args:
            task_identifier: The task identifier for the log.
            log_path: Absolute path to the log file.
        """
        existing_logs = self._get_logs()
        if log_path in existing_logs.get(task_identifier, set()):
            return

        new_data = pa.Table.from_pydict(
            {"task_identifier": [task_identifier], "log_path": [log_path]},
            schema=LOGS_SCHEMA,
        )

        self._database_path.mkdir(parents=True, exist_ok=True)

        if self._logs_table_exists():
            write_deltalake(
                self._logs_table_path,
                new_data,
                mode="append",
            )
        else:
            metadata = _create_table_metadata("logs", LOGS_TABLE_VERSION)
            write_deltalake(
                self._logs_table_path,
                new_data,
                description=json.dumps(metadata),
            )

    def search_for_logs(self, task_ids: set[str]) -> list[str]:
        """Search for logs matching the given task IDs.

        First searches the logs table for indexed logs, then falls back to
        scanning log directories for any remaining task IDs.

        Args:
            task_ids: Set of task identifiers to search for.

        Returns:
            List of log file paths for the best log of each task.
        """
        id_to_logs: dict[str, list[str]] = {}
        remaining_task_ids = set(task_ids)

        # First, search the logs table for indexed logs
        indexed_logs = self._get_logs()
        for task_id in list(remaining_task_ids):
            if task_id in indexed_logs:
                id_to_logs[task_id] = list(indexed_logs[task_id])
                remaining_task_ids.remove(task_id)

        # Fall back to scanning log directories for remaining task IDs
        if remaining_task_ids:
            log_dirs = self._get_log_dirs()
            for log_dir in log_dirs:
                logs = list_all_eval_logs(log_dir=log_dir)
                for log in logs:
                    if log.task_identifier in remaining_task_ids:
                        if log.task_identifier not in id_to_logs:
                            id_to_logs[log.task_identifier] = []
                        id_to_logs[log.task_identifier].append(log.info.name)

        # Find the best log for each id
        log_files: list[str] = []
        for logs in id_to_logs.values():
            best_log = None
            best_eval_log = None
            for log in logs:
                eval_log = read_eval_log(log, header_only=True)
                if is_better_log(eval_log, best_eval_log):
                    best_log = log
                    best_eval_log = eval_log
            if best_log:
                log_files.append(best_log)
        return log_files

    def _get_log_dirs(self) -> set[str]:
        """Read log directories from the Delta table.

        Returns:
            Set of log directory paths stored in the database.
        """
        if not self._log_dirs_table_exists():
            return set()

        dt = DeltaTable(self._log_dirs_table_path)
        table = dt.to_pyarrow_table()
        return set(table["log_dir"].to_pylist())

    def _get_logs(self) -> dict[str, set[str]]:
        """Read logs from the Delta table.

        Returns:
            Dictionary mapping task_identifier to set of log paths.
        """
        if not self._logs_table_exists():
            return {}

        dt = DeltaTable(self._logs_table_path)
        table = dt.to_pyarrow_table()

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
