from logging import getLogger
from pathlib import Path

from inspect_ai._eval.evalset import list_all_eval_logs
from inspect_ai.log import EvalLog, read_eval_log

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


def _get_database_path(spec: FlowSpec, base_dir: str) -> Path:
    if not spec.cache:
        raise ValueError("database must be set to get database path")
    database_file = Path(spec.cache) / "inspect_flow_db"
    return Path(absolute_path_relative_to(str(database_file), base_dir=base_dir))


def _get_log_dirs(spec: FlowSpec, base_dir: str) -> set[str]:
    database_path = _get_database_path(spec, base_dir=base_dir)
    if database_path.exists():
        with open(database_path, "r") as db_file:
            contents = db_file.read()
            lines = contents.splitlines()
            return set(lines)
    return set()


def init_database(spec: FlowSpec, base_dir: str) -> None:
    if not spec.cache:
        return
    database_path = _get_database_path(spec, base_dir=base_dir)
    if database_path.exists():
        logger.info(f"Existing database: {database_path}")
    else:
        logger.info(f"Creating database: {database_path}")


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
            if _is_better_log(eval_log, best_eval_log):
                best_log = log
                best_eval_log = eval_log
        if best_log:
            log_files.append(best_log)
    return log_files


def _is_better_log(candidate: EvalLog, best: EvalLog | None) -> bool:
    if not candidate.results or candidate.invalidated:
        return False
    if best is None:
        return True
    # Compare completed samples
    assert best.results
    if candidate.results.completed_samples > best.results.completed_samples:
        return True
    if candidate.results.completed_samples < best.results.completed_samples:
        return False
    # If completed samples are equal, take the more recently completed one
    return candidate.stats.completed_at > best.stats.completed_at
