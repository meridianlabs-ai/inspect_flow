from collections.abc import Callable
from typing import TypeAlias

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.task.util import slice_dataset  # TODO:ransom private import
from inspect_ai._util.notgiven import NOT_GIVEN  # TODO:ransom private import
from inspect_ai.agent import Agent
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create

from inspect_flow._types.types import (
    AgentConfig,
    CreateArgs,
    EpochsConfig,
    Matrix,
    ModelConfig,
    ModelRolesConfig,
    SolverConfig,
    TaskConfig,
)
from inspect_flow._util.list_util import (
    ensure_list,
    ensure_non_empty_list,
)
from inspect_flow._util.module_util import get_module_from_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

matrix_fields = ["args", "models", "model_roles", "solvers"]


class MatrixImpl:
    matrix: Matrix

    _models: list[Model] | None = None
    _args: list[CreateArgs] | None = None
    _model_roles: list[ModelRoles] | None = None
    _solvers: list[SingleSolver] | None = None

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
            self._models = create_models(self.matrix.models)
        if self.matrix.model_roles:
            self._model_roles = create_model_roles(self.matrix.model_roles)
        if self.matrix.solvers:
            self._solvers = create_solvers(self.matrix.solvers)

    def tasks(self) -> list[Task]:
        return [
            task
            for config in self.matrix.tasks
            for task in self.create_single_config_tasks(config)
        ]

    def create_single_config_tasks(self, config: TaskConfig) -> list[Task]:
        models = self._models or create_models(ensure_list(config.models))
        args_list = self._args or config.args
        model_role_list = self._model_roles or create_model_roles(
            ensure_list(config.model_roles)
        )
        solvers = self._solvers or create_solvers(ensure_list(config.solvers))

        task_func = get_task_creator(config)

        tasks = []
        for model in ensure_non_empty_list(models):
            for args in ensure_non_empty_list(args_list):
                for model_roles in ensure_non_empty_list(model_role_list):
                    for solver in ensure_non_empty_list(solvers):
                        if model:
                            # TODO:ransom avoid calling private API - inspect should support creating tasks with a model
                            init_active_model(model, GenerateConfig())
                        task = task_func(**(args or {}))

                        if config.sample_id is not None:
                            task.dataset = slice_dataset(
                                task.dataset,
                                limit=None,
                                sample_id=config.sample_id,
                            )

                        epochs = config.epochs
                        if isinstance(epochs, EpochsConfig):
                            epochs = Epochs(
                                epochs=epochs.epochs,
                                reducer=epochs.reducer,
                            )

                        def ng(arg):
                            """Pass NOT_GIVEN for args that are None"""
                            return arg if arg is not None else NOT_GIVEN

                        task_with(
                            task,
                            # dataset= Not Supported
                            # setup= Not Supported
                            solver=ng(solver),  # pyright: ignore[reportArgumentType] TODO:ransom
                            # cleanup= Not Supported
                            # scorer= Not Supported
                            # metrics= Not Supported
                            model=ng(model),
                            config=ng(config.config),
                            model_roles=ng(model_roles),
                            sandbox=ng(config.sandbox),
                            approval=ng(config.approval),  # type: ignore TODO:ransom
                            epochs=ng(epochs),
                            fail_on_error=ng(config.fail_on_error),
                            continue_on_fail=ng(config.continue_on_fail),
                            message_limit=ng(config.message_limit),
                            token_limit=ng(config.token_limit),
                            time_limit=ng(config.time_limit),
                            working_limit=ng(config.working_limit),
                            name=ng(config.name),
                            version=ng(config.version),
                            metadata=ng(config.metadata),
                        )
                        tasks.append(task)
        return tasks


def create_model(
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
        **(model_config.model_args or {}),
    )


def create_single_config_models(model_config: ModelConfig) -> list[Model]:
    generate_config_list = ensure_non_empty_list(model_config.config)
    return [
        create_model(model_config, generate_config)
        for generate_config in generate_config_list
    ]


def create_models(config: list[ModelConfig]) -> list[Model]:
    return [
        model
        for model_config in config
        for model in create_single_config_models(model_config)
    ]


def create_single_config_solvers(
    config: SolverConfig | list[SolverConfig] | AgentConfig,
) -> list[SingleSolver]:
    if isinstance(config, SolverConfig):
        args_list = ensure_non_empty_list(config.args)
        return [
            registry_create(type="solver", name=config.name, **(args or {}))
            for args in args_list
        ]
    if isinstance(config, AgentConfig):
        args_list = ensure_non_empty_list(config.args)
        return [
            registry_create(type="agent", name=config.name, **(args or {}))
            for args in args_list
        ]
    solver_chain = []
    for single_config in config:
        if single_config.args and len(single_config.args) > 1:
            raise ValueError("chained solvers may not provide multiple sets of args")
        solver_chain.extend(create_single_config_solvers(single_config))
    return [solver_chain]


def create_solvers(
    config: list[SolverConfig | list[SolverConfig] | AgentConfig],
) -> list[SingleSolver]:
    return [
        solver
        for solver_config in config
        for solver in create_single_config_solvers(solver_config)
    ]


def create_model_roles(config: list[ModelRolesConfig]) -> list[ModelRoles]:
    roles_list = []
    for roles_config in config:
        roles = {}
        for role, model_config in roles_config.items():
            model = model_config
            if isinstance(model, ModelConfig):
                if model.config and len(model.config) > 1:
                    raise ValueError(
                        "at most one config may be specified for models in model_roles"
                    )
                model = create_model(
                    model_config=model,
                    generate_config=model.config[0] if model.config else None,
                )
            roles[role] = model
        roles_list.append(roles)
    return roles_list


def get_task_creator(config: TaskConfig) -> Callable[..., Task]:
    if config.file:
        file_attr = config.file_attr or config.name
        if not file_attr:
            raise ValueError(
                f"file_attr or name not specified for task with file {config.file} "
            )
        module = get_module_from_file(config.file)
        task_func = getattr(module, file_attr)
    else:
        registry_name = config.registry_name or config.name
        if not registry_name:
            raise ValueError(
                "registry_name or name not specified for task without file"
            )

        def task_func(**kwargs):
            return registry_create(type="task", name=registry_name, **kwargs)

    return task_func
