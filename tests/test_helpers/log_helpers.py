import shutil
from itertools import product
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow._types.types import (
    BuiltinConfig,
    EvalSetConfig,
    ModelConfig,
    PackageConfig,
    TaskConfig,
)


def init_test_logs() -> str:
    # Remove logs/local_logs directory if it exists
    log_dir = (Path.cwd() / "logs" / "local_logs").resolve()
    if log_dir.exists():
        shutil.rmtree(log_dir)
    return str(log_dir)


def task_name(pkg: PackageConfig, item: TaskConfig) -> str:
    if pkg.package:
        return f"{pkg.name}/{item.name}"
    else:
        return item.name


def model_name(pkg: PackageConfig | BuiltinConfig, item: ModelConfig) -> str:
    if pkg.package:
        return f"{pkg.package}/{item.name}"
    else:
        return item.name


def verify_test_logs(config: EvalSetConfig, log_dir: str) -> None:
    # Check that logs/local_logs directory was created
    assert Path(log_dir).exists()
    log_list = list_eval_logs(log_dir)

    tasks = [task_name(pkg, item) for pkg in config.tasks for item in pkg.items]
    models = (
        [model_name(pkg, item) for pkg in config.models for item in pkg.items]
        if config.models
        else []
    )

    assert len(log_list) == len(tasks) * len(models)
    logs = [read_eval_log(log) for log in log_list]
    assert all(log.status == "success" for log in logs), (
        "All logs should have status 'success'"
    )
    assert sorted([(log.eval.task, log.eval.model) for log in logs]) == sorted(
        product(tasks, models)
    )
