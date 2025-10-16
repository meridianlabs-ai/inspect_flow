from typing import Any
import inspect_ai
import yaml
from inspect_ai import Task
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.util import registry_create

from inspect_flow._types.types import FlowConfig, FlowOptions, ModelConfig, TaskConfig
from inspect_flow._util.list_util import ensure_list, ensure_non_empty_list, flatten
from inspect_flow._util.module_util import get_module_from_file


def read_config() -> FlowConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowConfig(**data)


def create_single_config_tasks(
    config: TaskConfig, args: list[dict[str, Any]], models: list[Model]
) -> list[Task]:
    if len(models) and config.models:
        raise ValueError("Only one of matrix and task may specify model")

    models_or_none: list[Model | None] = []
    if len(models):
        models_or_none = list(models)
    elif config.models:
        models_or_none = list(create_models(ensure_list(config.models)))
    else:
        models_or_none = [None]

    if config.file:
        module = get_module_from_file(config.file)
        task_func = getattr(module, config.name)
    else:

        def task_func(**kwargs):
            return registry_create(type="task", name=config.name, **kwargs)

    def create_tasks_with_model(model: Model | None) -> list[Task]:
        if model:
            # TODO:ransom avoid calling private API - inspect should support creating tasks with a model
            init_active_model(model, GenerateConfig())
        tasks = [
            task_func(**(args or {})) for args in ensure_non_empty_list(config.args)
        ]
        # TODO:ransom use task_with?
        if model:
            for task in tasks:
                task.model = model
        return tasks

    return flatten([create_tasks_with_model(model) for model in models_or_none])


def create_tasks(config: list[TaskConfig], models: list[Model]) -> list[Task]:
    task_lists = [
        create_single_config_tasks(task_config, models) for task_config in config
    ]
    return flatten(task_lists)


def run_eval_set(config: FlowConfig) -> tuple[bool, list[EvalLog]]:
    args = ensure_list(config.matrix.args)
    models = create_models(ensure_list(config.matrix.models))
    tasks = create_tasks(ensure_list(config.matrix.tasks), args, models)

    options = config.options or FlowOptions(log_dir=".")
    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=options.log_dir,
        limit=options.limit,
    )


def main() -> None:
    config = read_config()
    run_eval_set(config)


if __name__ == "__main__":
    main()
