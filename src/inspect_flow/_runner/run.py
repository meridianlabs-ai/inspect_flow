import json

import inspect_ai
from inspect_ai import Task
from inspect_ai.log import EvalLog
from inspect_ai.model import Model

from inspect_flow._types.types import (
    BuiltinConfig,
    EvalSetConfig,
    ModelConfig,
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


def _load_task(task_name: str, task_config: TaskConfig):
    task = inspect_ai.util.registry_create(
        "task", task_name, **(task_config.args or {})
    )
    return task


def _load_tasks(
    task_configs: list[PackageConfig[TaskConfig]],
) -> list[Task]:
    task_names, items = zip(
        *[
            (_get_qualified_name(pkg, item), item)
            for pkg in task_configs
            for item in pkg.items
        ],
        strict=True,
    )
    tasks = [*map(_load_task, task_names, items)]
    return tasks


def _get_model_from_config(
    model_package_config: PackageConfig[ModelConfig] | BuiltinConfig[ModelConfig],
    model_config: ModelConfig,
) -> Model:
    qualified_name = _get_qualified_name(model_package_config, model_config)

    if model_config.args is None:
        return inspect_ai.model.get_model(qualified_name)

    args_except_config = {
        **model_config.args.model_dump(exclude={"raw_config"}),
        **(model_config.args.model_extra or {}),
    }
    if model_config.args.parsed_config is None:
        return inspect_ai.model.get_model(
            qualified_name,
            **args_except_config,
        )

    return inspect_ai.model.get_model(
        qualified_name,
        config=model_config.args.parsed_config,
        **args_except_config,
    )


def run_eval_set(eval_set_config: EvalSetConfig) -> tuple[bool, list[EvalLog]]:
    tasks = _load_tasks(eval_set_config.tasks)

    models: list[Model] | None = None
    if eval_set_config.models:
        models = [
            _get_model_from_config(model_package_config, item)
            for model_package_config in eval_set_config.models
            for item in model_package_config.items
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
