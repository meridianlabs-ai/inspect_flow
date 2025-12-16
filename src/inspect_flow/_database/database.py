from pathlib import Path

from inspect_ai._eval.evalset import list_all_eval_logs

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.path_util import absolute_path_relative_to


def _get_database_path(spec: FlowSpec, base_dir: str) -> Path:
    if not spec.database:
        raise ValueError("database must be set to get database path")
    database_file = Path(spec.database) / "inspect_flow_db"
    return Path(absolute_path_relative_to(str(database_file), base_dir=base_dir))


def _get_log_dirs(spec: FlowSpec, base_dir: str) -> set[str]:
    database_path = _get_database_path(spec, base_dir=base_dir)
    if database_path.exists():
        with open(database_path, "r") as db_file:
            contents = db_file.read()
            lines = contents.splitlines()
            return set(lines)
    return set()


def add_log_dir(spec: FlowSpec, base_dir: str) -> None:
    if not spec.log_dir:
        raise ValueError("log_dir must be set to add to database")
    previous_log_dirs = _get_log_dirs(spec, base_dir=base_dir)
    log_dir = absolute_path_relative_to(spec.log_dir, base_dir=base_dir)
    new_paths = previous_log_dirs.union({log_dir})
    if new_paths != previous_log_dirs:
        database_path = _get_database_path(spec, base_dir=base_dir)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with open(database_path, "w") as db_file:
            db_file.write("\n".join(sorted(new_paths)) + "\n")


def search_for_logs(task_ids: set[str], spec: FlowSpec, base_dir: str) -> list[str]:
    log_dirs = _get_log_dirs(spec, base_dir=base_dir)
    log_files = []
    for log_dir in log_dirs:
        logs = list_all_eval_logs(log_dir=log_dir)
        for log in logs:
            if log.task_identifier in task_ids:
                log_files.append(log.info.name)
                task_ids.remove(log.task_identifier)
                if not task_ids:
                    return log_files
    return log_files
