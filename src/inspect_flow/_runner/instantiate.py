from collections.abc import Callable
from typing import TypeAlias, TypeVar

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.task.util import slice_dataset
from inspect_ai._util.notgiven import NOT_GIVEN
from inspect_ai.agent import Agent
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create
from pydantic import BaseModel

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowConfig,
    FlowEpochs,
    FlowModel,
    FlowSolver,
    FlowTask,
    ModelRolesConfig,
)
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


def instantiate_tasks(config: FlowConfig) -> list[Task]:
    return [
        _instantiate_task(config, task_config) for task_config in config.tasks or []
    ]


def _create_model(config: FlowModel) -> Model:
    if not config.name:
        raise ValueError(f"Model name is required. Model: {config}")

    return get_model(
        model=config.name,
        role=config.role,
        default=config.default,
        config=config.config or GenerateConfig(),
        base_url=config.base_url,
        api_key=config.api_key,
        memoize=config.memoize or True,
        **(config.model_args or {}),
    )


def _create_model_roles(config: ModelRolesConfig) -> ModelRoles:
    roles = {}
    for role, model_config in config.items():
        model = model_config
        if isinstance(model, FlowModel):
            model = _create_model(config=model)
        roles[role] = model
    return roles


def _create_single_solver(config: str | FlowSolver) -> Solver:
    if not isinstance(config, FlowSolver):
        raise ValueError(f"Solver should have been resolved. Solver: {config}")
    if not config.name:
        raise ValueError(f"Solver name is required. Solver: {config}")

    return registry_create(type="solver", name=config.name, **(config.args or {}))


def _create_agent(config: FlowAgent) -> Agent:
    if not config.name:
        raise ValueError(f"Agent name is required. Agent: {config}")

    return registry_create(type="agent", name=config.name, **(config.args or {}))


def _create_solver(
    config: FlowSolver | list[str | FlowSolver] | FlowAgent,
) -> SingleSolver:
    if isinstance(config, FlowSolver):
        return _create_single_solver(config)
    if isinstance(config, FlowAgent):
        return _create_agent(config)
    return [_create_single_solver(single_config) for single_config in config]


def _instantiate_task(flow_config: FlowConfig, config: str | FlowTask) -> Task:
    if (
        flow_config.defaults is not None
        or not isinstance(config, FlowTask)
        or isinstance(config.model, str)
        or isinstance(config.solver, str)
    ):
        raise ValueError("config must be resolved before calling instantiate_task")

    model = _create_model(config.model) if config.model else None
    solver = _create_solver(config.solver) if config.solver else None
    model_roles = (
        _create_model_roles(config.model_roles) if config.model_roles else None
    )
    task_func = _get_task_creator(config)
    if model:
        init_active_model(model, model.config)
    task = task_func(**(config.args or {}))

    if config.sample_id is not None:
        task.dataset = slice_dataset(
            task.dataset,
            limit=None,
            sample_id=config.sample_id,
        )

    epochs = config.epochs
    if isinstance(epochs, FlowEpochs):
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
        solver=ng(solver),
        # cleanup= Not Supported
        # scorer= Not Supported
        # metrics= Not Supported
        model=ng(model),
        config=ng(config.config),
        model_roles=ng(model_roles),
        sandbox=ng(config.sandbox),
        approval=ng(config.approval),
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
    return task


def _get_task_creator_from_file(file_path: str, attr: str) -> Callable[..., Task]:
    file = find_file(file_path)
    if not file:
        raise FileNotFoundError(f"File not found: {file_path}")

    module = get_module_from_file(file)
    return getattr(module, attr)


def _get_task_creator(config: FlowTask) -> Callable[..., Task]:
    if not config.name:
        raise ValueError(f"Task name is required. Task: {config}")
    config_name = config.name

    if config.name.find("@") != -1:
        file, attr = config.name.split("@", 1)
        return _get_task_creator_from_file(file, attr)
    else:

        def task_func(**kwargs):
            return registry_create(type="task", name=config_name, **kwargs)

        return task_func
