import shutil
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow import FlowConfig, FlowTask
from pydantic_core import to_jsonable_python


def init_test_logs() -> str:
    relative_log_dir = "logs/flow_test"
    # Remove logs/flow_test directory if it exists
    log_dir = (Path.cwd() / relative_log_dir).resolve()
    if log_dir.exists():
        shutil.rmtree(log_dir)
    return relative_log_dir


def _task_and_model(config: str | FlowTask) -> tuple[str | None, str | None]:
    if isinstance(config, str):
        return config, None
    else:
        return config.name, config.model_name


def verify_test_logs(config: FlowConfig | FlowConfig, log_dir: str) -> None:
    if isinstance(config, FlowConfig):
        config = FlowConfig.model_validate(to_jsonable_python(config))
    # Check that logs/flow_test directory was created
    assert Path(log_dir).exists()
    log_list = list_eval_logs(log_dir)

    assert len(log_list) == len(config.tasks or [])
    logs = [read_eval_log(log) for log in log_list]
    assert all(log.status == "success" for log in logs), (
        "All logs should have status 'success'"
    )
    assert sorted([(log.eval.task, log.eval.model) for log in logs]) == sorted(
        [_task_and_model(task) for task in config.tasks or []]
    )
