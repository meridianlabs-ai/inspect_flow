from collections.abc import Generator
from dataclasses import dataclass

from inspect_ai import Task
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.util import registry_create

from inspect_flow._types.types import (
    FlowConfig,
    Matrix,
    ModelConfig,
    TaskArgs,
    TaskConfig,
)
from inspect_flow._util.list_util import (
    ensure_list,
    ensure_non_empty_list,
    flatten,
)
from inspect_flow._util.module_util import get_module_from_file

matrix_fields = ["args", "models"]


class MatrixImpl:
    matrix: Matrix

    _models: list[Model] | None = None
    _args: list[TaskArgs] | None = None

    def __init__(self, matrix: Matrix):
        self.matrix = matrix
        self.validate_config()
        self.create_matrix()

    def validate_config(self) -> None:
        for task in self.matrix.tasks:
            for field in matrix_fields:
                if getattr(task, field, None) and getattr(self.matrix, field, None):
                    raise ValueError(f"Only one of matrix and task may specify {field}")

    def create_matrix(self) -> None:
        self._args = self.matrix.args
        if self.matrix.models:
            self._models = create_models(ensure_list(self.matrix.models))

    def tasks(self) -> list[Task]:
        return [
            task
            for config in self.matrix.tasks
            for task in self.create_single_config_tasks(config)
        ]

    def create_single_config_tasks(self, config: TaskConfig) -> list[Task]:
        models = self._models or create_models(ensure_list(config.models))
        args_list = self._args or config.args

        if config.file:
            module = get_module_from_file(config.file)
            task_func = getattr(module, config.name)
        else:

            def task_func(**kwargs):
                return registry_create(type="task", name=config.name, **kwargs)

        tasks = []
        for model in ensure_non_empty_list(models):
            for args in ensure_non_empty_list(args_list):
                if model:
                    # TODO:ransom avoid calling private API - inspect should support creating tasks with a model
                    init_active_model(model, GenerateConfig())
                task = task_func(**(args or {}))
                # TODO:ransom use task_with?
                if model:
                    task.model = model
                tasks.append(task)
        return tasks


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
    return flatten(model_lists)
