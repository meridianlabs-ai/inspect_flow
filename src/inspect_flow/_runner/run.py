from functools import lru_cache
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from itertools import chain
from pathlib import Path
from types import ModuleType

import inspect_ai
import yaml
from inspect_ai import Task
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.util import registry_create

from inspect_flow._types.types import FlowConfig, FlowOptions, ModelConfig, TaskConfig
from inspect_flow._util.util import ensure_list, ensure_non_empty_list


def read_config() -> FlowConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowConfig(**data)


def create_single_model(
    model_config: ModelConfig, generate_config: GenerateConfig | None
) -> Model:
    return get_model(
        model=model_config.name,
        role=model_config.role,
        default=model_config.default,
        config=generate_config or GenerateConfig(),
        base_url=model_config.base_url,
        api_key=model_config.api_key,
        memoize=model_config.memoize,
    )


def create_model(model_config: ModelConfig) -> list[Model]:
    generate_config_list = ensure_non_empty_list(model_config.config)
    return [
        create_single_model(model_config, generate_config)
        for generate_config in generate_config_list
    ]


def create_models(config: list[ModelConfig]) -> list[Model]:
    model_lists = [create_model(model_config) for model_config in config]
    return list(chain.from_iterable(model_lists))


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


def create_tasks_from_file(file: str, config: TaskConfig) -> list[Task]:
    module = get_module_from_file(file)
    if not hasattr(module, config.name):
        raise ValueError(f"Function '{config.name}' not found in {file}")
    task_func = getattr(module, config.name)

    return [task_func(**(args or {})) for args in ensure_non_empty_list(config.args)]


def create_tasks_from_registry(config: TaskConfig) -> list[Task]:
    return [
        registry_create(type="task", name=config.name, **(args or {}))
        for args in ensure_non_empty_list(config.args)
    ]


def create_single_config_tasks(config: TaskConfig, model: Model) -> list[Task]:
    # TODO:ransom avoid calling private API - inspect should support creating tasks with a model
    init_active_model(model, GenerateConfig())
    if config.file:
        tasks = create_tasks_from_file(config.file, config)
    else:
        tasks = create_tasks_from_registry(config)
    # TODO:ransom use task_with?
    for task in tasks:
        task.model = model
    return tasks


def create_tasks(config: list[TaskConfig], models: list[Model]) -> list[Task]:
    task_lists = [
        create_single_config_tasks(task_config, model)
        for model in models
        for task_config in config
    ]
    return list(chain.from_iterable(task_lists))


def run_eval_set(config: FlowConfig) -> tuple[bool, list[EvalLog]]:
    models = create_models(ensure_list(config.matrix.models))
    tasks = create_tasks(ensure_list(config.matrix.tasks), models)

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
