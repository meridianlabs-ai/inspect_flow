import shutil
from itertools import product
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow._types.types import (
    FlowConfig,
)
from inspect_flow._util.util import ensure_list


def init_test_logs() -> str:
    # Remove logs/local_logs directory if it exists
    log_dir = (Path.cwd() / "logs" / "local_logs").resolve()
    if log_dir.exists():
        shutil.rmtree(log_dir)
    return str(log_dir)


def verify_test_logs(config: FlowConfig, log_dir: str) -> None:
    # Check that logs/local_logs directory was created
    assert Path(log_dir).exists()
    log_list = list_eval_logs(log_dir)

    tasks = [task.name for task in ensure_list(config.matrix.tasks)]
    models = [model.name for model in ensure_list(config.matrix.models)]

    assert len(log_list) == len(tasks) * len(models)
    logs = [read_eval_log(log) for log in log_list]
    assert all(log.status == "success" for log in logs), (
        "All logs should have status 'success'"
    )
    assert sorted([(log.eval.task, log.eval.model) for log in logs]) == sorted(
        product(tasks, models)
    )
