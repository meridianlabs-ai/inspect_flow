from collections.abc import Callable
from typing import TypeAlias, TypeVar

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.task.util import slice_dataset
from inspect_ai._util.notgiven import NOT_GIVEN
from inspect_ai._util.notgiven import NotGiven as InspectNotGiven
from inspect_ai.agent import Agent
from inspect_ai.model import Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create
from pydantic import BaseModel

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowEpochs,
    FlowJob,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
    ModelRolesConfig,
    NotGiven,
)
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


def instantiate_tasks(job: FlowJob, base_dir: str) -> list[Task]:
    return [
        _instantiate_task(job, task_config, base_dir=base_dir)
        for task_config in job.tasks or []
    ]


def _create_model(model: FlowModel) -> Model:
    if not model.name:
        raise ValueError(f"Model name is required. Model: {model}")

    return get_model(
        model=model.name,
        role=model.role,
        default=model.default,
        config=model.config or GenerateConfig(),
        base_url=model.base_url,
        api_key=model.api_key,
        memoize=model.memoize or True,
        **(model.model_args or {}),
    )


def _create_model_roles(model_roles: ModelRolesConfig) -> ModelRoles:
    roles = {}
    for role, model in model_roles.items():
        if isinstance(model, FlowModel):
            model = _create_model(model=model)
        roles[role] = model
    return roles


def _create_single_solver(solver: str | FlowSolver) -> Solver:
    if not isinstance(solver, FlowSolver):
        raise ValueError(f"Solver should have been resolved. Solver: {solver}")
    if not solver.name:
        raise ValueError(f"Solver name is required. Solver: {solver}")

    return registry_create(type="solver", name=solver.name, **(solver.args or {}))


def _create_agent(agent: FlowAgent) -> Agent:
    if not agent.name:
        raise ValueError(f"Agent name is required. Agent: {agent}")

    return registry_create(type="agent", name=agent.name, **(agent.args or {}))


def _create_solver(
    solver: FlowSolver | list[str | FlowSolver] | FlowAgent,
) -> SingleSolver:
    if isinstance(solver, FlowSolver):
        return _create_single_solver(solver)
    if isinstance(solver, FlowAgent):
        return _create_agent(solver)
    return [_create_single_solver(single_solver) for single_solver in solver]


def _instantiate_task(job: FlowJob, flow_task: str | FlowTask, base_dir: str) -> Task:
    if (
        job.defaults is not None
        or not isinstance(flow_task, FlowTask)
        or isinstance(flow_task.model, str)
        or isinstance(flow_task.solver, str)
    ):
        raise ValueError("config must be resolved before calling instantiate_task")

    # make sure this differentiates between None and NotGiven
    model = _create_model(flow_task.model) if flow_task.model else NOT_GIVEN
    solver = _create_solver(flow_task.solver) if flow_task.solver else NOT_GIVEN
    model_roles = (
        _create_model_roles(flow_task.model_roles)
        if flow_task.model_roles
        else NOT_GIVEN
    )
    task_func = _get_task_creator(flow_task, base_dir=base_dir)
    if model:
        init_active_model(model, model.config)
    task = task_func(**(flow_task.args or {}))

    if flow_task.sample_id is not None:
        task.dataset = slice_dataset(
            task.dataset,
            limit=None,
            sample_id=flow_task.sample_id,
        )

    epochs = flow_task.epochs
    if isinstance(epochs, FlowEpochs):
        epochs = Epochs(
            epochs=epochs.epochs,
            reducer=epochs.reducer,
        )

    _T = TypeVar("_T")

    def ng(value: _T | NotGiven) -> _T | InspectNotGiven:
        return NOT_GIVEN if isinstance(value, NotGiven) else value

    task_with(
        task,
        # dataset= Not Supported
        # setup= Not Supported
        solver=solver,
        # cleanup= Not Supported
        # scorer= Not Supported
        # metrics= Not Supported
        model=model,
        config=ng(flow_task.config),
        model_roles=model_roles,
        sandbox=ng(flow_task.sandbox),
        approval=ng(flow_task.approval),
        epochs=ng(epochs),
        fail_on_error=ng(flow_task.fail_on_error),
        continue_on_fail=ng(flow_task.continue_on_fail),
        message_limit=ng(flow_task.message_limit),
        token_limit=ng(flow_task.token_limit),
        time_limit=ng(flow_task.time_limit),
        working_limit=ng(flow_task.working_limit),
        name=ng(flow_task.name),
        version=ng(flow_task.version),
        metadata=ng(flow_task.metadata),
    )
    return task


def _get_task_creator_from_file(
    file_path: str, base_dir: str, attr: str
) -> Callable[..., Task]:
    file = find_file(file_path, base_dir=base_dir)
    if not file:
        raise FileNotFoundError(f"File not found: {file_path}")

    module = get_module_from_file(file)
    return getattr(module, attr)


def _get_task_creator(task: FlowTask, base_dir: str) -> Callable[..., Task]:
    if not task.name:
        raise ValueError(f"Task name is required. Task: {task}")
    config_name = task.name

    if task.name.find("@") != -1:
        file, attr = task.name.split("@", 1)
        return _get_task_creator_from_file(file, base_dir=base_dir, attr=attr)
    else:

        def task_func(**kwargs):
            return registry_create(type="task", name=config_name, **kwargs)

        return task_func
