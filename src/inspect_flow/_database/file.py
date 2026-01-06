from logging import getLogger
from pathlib import Path

from inspect_ai._eval.evalset import list_all_eval_logs
from inspect_ai.log import read_eval_log

from inspect_flow._database.database import FlowDatabase, is_better_log

logger = getLogger(__name__)


class FileDatabase(FlowDatabase):
    """File-based implementation of FlowDatabase.

    Stores log directory paths in a simple text file, one path per line.
    """

    def __init__(self, database_path: Path) -> None:
        """Initialize the FileDatabase.

        Args:
            database_path: Path to the database file.
        """
        self._database_path = database_path
        if self._database_path.exists():
            logger.info(f"Existing database: {self._database_path}")
        else:
            logger.info(f"Creating database: {self._database_path}")

    def add_log_dir(self, log_dir: str) -> None:
        """Add a log directory to the database.

        Args:
            log_dir: Absolute path to the log directory to add.
        """
        previous_log_dirs = self._get_log_dirs()
        new_paths = previous_log_dirs.union({log_dir})
        if new_paths != previous_log_dirs:
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._database_path, "w") as db_file:
                db_file.write("\n".join(sorted(new_paths)) + "\n")

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
        """Read log directories from the database file.

        Returns:
            Set of log directory paths stored in the database.
        """
        if self._database_path.exists():
            with open(self._database_path, "r") as db_file:
                contents = db_file.read()
                lines = contents.splitlines()
                return set(lines)
        return set()
