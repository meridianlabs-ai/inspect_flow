import shutil
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow._types.flow_types import (
    FConfig,
)
from inspect_flow.types import FlowConfig
from pydantic_core import to_jsonable_python


def init_test_logs() -> str:
    # Remove logs/local_logs directory if it exists
    log_dir = (Path.cwd() / "logs" / "local_logs").resolve()
    if log_dir.exists():
        shutil.rmtree(log_dir)
    return str(log_dir)


def verify_test_logs(config: FConfig | FlowConfig, log_dir: str) -> None:
    if isinstance(config, FlowConfig):
        config = FConfig.model_validate(to_jsonable_python(config))
    # Check that logs/local_logs directory was created
    assert Path(log_dir).exists()
    log_list = list_eval_logs(log_dir)

    assert len(log_list) == len(config.tasks or [])
    logs = [read_eval_log(log) for log in log_list]
    assert all(log.status == "success" for log in logs), (
        "All logs should have status 'success'"
    )
    assert sorted([(log.eval.task, log.eval.model) for log in logs]) == sorted(
        [
            (task.name, task.model.name if task.model else None)
            for task in config.tasks or []
        ]
    )
