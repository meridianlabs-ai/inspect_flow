from logging import getLogger
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from inspect_ai._eval.evalset import list_all_eval_logs
from inspect_ai.log import read_eval_log

from inspect_flow._database.database import FlowDatabase, is_better_log

logger = getLogger(__name__)

LOG_DIRS_SCHEMA = pa.schema(
    [
        ("log_dir", pa.string()),
    ]
)


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
        self._table_path = str(database_path / "log_dirs")
        if self._table_exists():
            logger.info(f"Existing database: {self._database_path}")
        else:
            logger.info(f"Creating database: {self._database_path}")

    def _table_exists(self) -> bool:
        """Check if the Delta table exists."""
        try:
            DeltaTable(self._table_path)
            return True
        except TableNotFoundError:
            return False

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

        write_deltalake(
            self._table_path,
            new_data,
            mode="append",
        )

    def search_for_logs(self, task_ids: set[str]) -> list[str]:
        """Search for logs matching the given task IDs.

        Args:
            task_ids: Set of task identifiers to search for.

        Returns:
            List of log file paths for the best log of each task.
        """
        log_dirs = self._get_log_dirs()
        id_to_logs: dict[str, list[str]] = {}

        for log_dir in log_dirs:
            logs = list_all_eval_logs(log_dir=log_dir)
            for log in logs:
                if log.task_identifier in task_ids:
                    if log.task_identifier not in id_to_logs:
                        id_to_logs[log.task_identifier] = []
                    id_to_logs[log.task_identifier].append(log.info.name)

        # find the best log for each id
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
        if not self._table_exists():
            return set()

        dt = DeltaTable(self._table_path)
        table = dt.to_pyarrow_table()
        return set(table["log_dir"].to_pylist())
