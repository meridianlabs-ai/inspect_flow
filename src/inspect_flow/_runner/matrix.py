from collections.abc import Generator
from dataclasses import dataclass

from inspect_ai.model import GenerateConfig, Model, get_model

from inspect_flow._types.types import FlowConfig, Matrix, ModelConfig, TaskArgs
from inspect_flow._util.list_util import (
    ensure_list,
    ensure_list_or_none,
    ensure_non_empty_list,
    flatten,
)

matrix_fields = ["args", "models"]


@dataclass
class MatrixItem:
    model: Model | None
    args: TaskArgs


@dataclass
class MatrixImpl:
    config: FlowConfig
    matrix: Matrix

    _models: list[Model] | None
    _args: list[TaskArgs] | None

    def __post_init__(self):
        self.validate_config()
        self.create_matrix()

    def validate_config(self) -> None:
        for task in ensure_list(self.matrix.tasks):
            for field in matrix_fields:
                if getattr(task, field, None) and getattr(self.matrix, field, None):
                    raise ValueError(f"Only one of matrix and task may specify {field}")

    def create_matrix(self) -> None:
        self._args = ensure_list_or_none(self.matrix.args)
        if self.matrix.models:
            self._models = create_models(ensure_list(self.matrix.models))

    def items(self) -> Generator[MatrixItem, None, None]:
        for task_config in ensure_list(self.matrix.tasks):
            for model in ensure_non_empty_list(
                self._models or create_models(ensure_list(task_config.models))
            ):
                for args in ensure_non_empty_list(
                    self._args or ensure_list(task_config.args)
                ):
                    yield MatrixItem(model=model, args=args)


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
