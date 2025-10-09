import json

import inspect_ai
from inspect_ai import Task
from inspect_ai.log import EvalLog
from inspect_ai.util import registry_create

from inspect_flow._types.types import (
    BuiltinConfig,
    EvalSetConfig,
    PackageConfig,
    T,
    TaskConfig,
    TaskGroupConfig,
)


def read_config() -> TaskGroupConfig:
    with open("task_group.json", "r") as f:
        data = json.load(f)
        return TaskGroupConfig(**data)


def _get_qualified_name(
    config: PackageConfig[T] | BuiltinConfig[T],
    item: T,
) -> str:
    if isinstance(config, BuiltinConfig):
        return item.name

    return f"{config.name}/{item.name}"


def create_task(pkg: PackageConfig[TaskConfig], item: TaskConfig) -> Task:
    task = registry_create(
        type="task", name=_get_qualified_name(pkg, item), **(item.args or {})
    )
    return task


def create_tasks(config: list[PackageConfig[TaskConfig]]) -> list[Task]:
    return [create_task(pkg, item) for pkg in config for item in pkg.items]


def run_eval_set(eval_set_config: EvalSetConfig) -> tuple[bool, list[EvalLog]]:
    tasks = create_tasks(eval_set_config.tasks)

    models = [
        _get_qualified_name(pkg, item)
        for pkg in eval_set_config.models or []
        for item in pkg.items
    ]

    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=eval_set_config.log_dir,
        model=models,
        limit=eval_set_config.limit,
    )


def main() -> None:
    config = read_config()
    eval_set_config = config.eval_set
    run_eval_set(eval_set_config)


if __name__ == "__main__":
    main()
