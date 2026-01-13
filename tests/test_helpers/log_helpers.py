import shutil
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow import FlowSpec, FlowTask
from inspect_flow._types.flow_types import NotGiven


def init_test_logs() -> str:
    relative_log_dir = "logs/flow_test"
    # Remove logs/flow_test directory if it exists
    log_dir = (Path.cwd() / relative_log_dir).resolve()
    if log_dir.exists():
        shutil.rmtree(log_dir)
    return str(log_dir)


def init_test_store() -> str:
    relative_db_dir = "logs/test_store"
    db_dir = (Path.cwd() / relative_db_dir).resolve()
    if db_dir.exists():
        shutil.rmtree(db_dir)
    return str(db_dir)


def _task_and_model(task: str | FlowTask) -> tuple[str | None, str | None | NotGiven]:
    if isinstance(task, str):
        return task, None
    else:
        return task.name if task.name else None, task.model_name


def verify_test_logs(spec: FlowSpec, log_dir: str) -> None:
    # Check that logs/flow_test directory was created
    if not log_dir.startswith("s3://"):
        assert Path(log_dir).exists()
    log_list = list_eval_logs(log_dir)

    assert len(log_list) == len(spec.tasks or [])
    logs = [read_eval_log(log) for log in log_list]
    assert all(log.status == "success" for log in logs), (
        "All logs should have status 'success'"
    )
    assert sorted([(log.eval.task, log.eval.model) for log in logs]) == sorted(
        [_task_and_model(task) for task in spec.tasks or []]
    )
