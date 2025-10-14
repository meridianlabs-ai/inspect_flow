import json
from functools import lru_cache
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType

import inspect_ai
from inspect_ai import Task
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.util import registry_create

from inspect_flow._types.types import (
    BuiltinConfig,
    EvalSetConfig,
    GetModelArgs,
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


def create_model(
    pkg: PackageConfig[ModelConfig] | BuiltinConfig[ModelConfig], item: ModelConfig
) -> Model:
    args: GetModelArgs = item.args or GetModelArgs()
    return get_model(
        model=_get_qualified_name(pkg, item),
        role=args.role,
        default=args.default,
        config=args.config or GenerateConfig(),
        base_url=args.base_url,
        api_key=args.api_key,
        memoize=args.memoize,
    )


def create_models(
    config: list[PackageConfig[ModelConfig] | BuiltinConfig[ModelConfig]],
) -> list[Model]:
    return [create_model(pkg, item) for pkg in config for item in pkg.items]


@lru_cache(maxsize=None)
def get_module_from_file(file: str) -> ModuleType:
    module_path = Path(file).resolve()
    module_name = module_path.as_posix()
    loader = SourceFileLoader(module_name, module_path.absolute().as_posix())
    spec = spec_from_loader(loader.name, loader)
    if not spec:
        raise ModuleNotFoundError(f"Module {module_name} not found")
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


def create_task_from_file(file: str, item: TaskConfig) -> Task:
    module = get_module_from_file(file)
    if not hasattr(module, item.name):
        raise ValueError(f"Function '{item.name}' not found in {file}")
    task_func = getattr(module, item.name)

    return task_func(**(item.args or {}))


def create_task(pkg: PackageConfig[TaskConfig], item: TaskConfig, model: Model) -> Task:
    # TODO:ransom avoid calling private API - inspect should support creating tasks with a model
    init_active_model(model, GenerateConfig())
    if pkg.package:
        task = registry_create(
            type="task",
            name=_get_qualified_name(pkg, item),
            **(item.args or {}),
        )
    else:
        assert pkg.file, "package or file is required"
        task = create_task_from_file(pkg.file, item)
    task.model = model
    return task


def create_tasks(
    config: list[PackageConfig[TaskConfig]], models: list[Model]
) -> list[Task]:
    return [
        create_task(pkg, item, model)
        for model in models
        for pkg in config
        for item in pkg.items
    ]


def run_eval_set(eval_set_config: EvalSetConfig) -> tuple[bool, list[EvalLog]]:
    models = create_models(eval_set_config.models or [])
    tasks = create_tasks(eval_set_config.tasks, models)

    # Do not pass models to eval_set as the models have already been set on the tasks
    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=eval_set_config.log_dir,
        limit=eval_set_config.limit,
    )


def main() -> None:
    config = read_config()
    eval_set_config = config.eval_set
    run_eval_set(eval_set_config)


if __name__ == "__main__":
    main()
