from collections.abc import Callable
from typing import Any, Mapping, Sequence, TypeAlias, TypeVar

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.loader import scorer_from_spec
from inspect_ai._eval.task.util import slice_dataset
from inspect_ai._util.notgiven import NOT_GIVEN
from inspect_ai._util.notgiven import NotGiven as InspectNotGiven
from inspect_ai._util.registry import (
    is_model_dict,
    is_registry_dict,
    model_create_from_dict,
)
from inspect_ai.agent import Agent
from inspect_ai.model import Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.scorer import Scorer
from inspect_ai.scorer._scorer import ScorerSpec
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create
from pydantic import BaseModel
from typing_extensions import Literal

from inspect_flow._types.flow_types import (
    CreateArgs,
    FlowAgent,
    FlowEpochs,
    FlowModel,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowTask,
    GenerateConfig,
    ModelRolesConfig,
    NotGiven,
)
from inspect_flow._util.list_util import sequence_to_list
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.not_given import default, default_none, is_set
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


# TODO:ransom copied from inspect_ai._util.registry for bug fix - remove once fixed
def _registry_arg(arg: Any) -> Any:
    if isinstance(arg, dict):
        if is_registry_dict(arg):
            return registry_create(arg["type"], arg["name"], **arg["params"])
        elif is_model_dict(arg):
            return model_create_from_dict(arg)
        else:
            return {k: _registry_arg(v) for k, v in arg.items()}
    elif isinstance(arg, (list, tuple)):
        return [_registry_arg(item) for item in arg]
    else:
        return arg


def _registry_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve any registry and model dicts in the given kwargs."""
    return {k: _registry_arg(v) for k, v in kwargs.items()}


def _kwargs(
    type: Literal["model", "solver", "scorer", "agent"],
    args: CreateArgs | None | NotGiven,
    task: FlowTask,
) -> dict[str, Any]:
    base_args = args or {}
    additional_args: CreateArgs = (
        task.extra_args and getattr(task.extra_args, type) or {}
    )
    return _registry_kwargs({**base_args, **additional_args})


def instantiate_tasks(spec: FlowSpec, base_dir: str) -> list[Task]:
    return [
        _instantiate_task(spec, task_config, base_dir=base_dir)
        for task_config in spec.tasks or []
    ]


def _create_model(task: FlowTask, model: FlowModel) -> Model:
    if not model.name:
        raise ValueError(f"Model name is required. Model: {model}")

    return get_model(
        model=model.name,
        role=default_none(model.role),
        default=default_none(model.default),
        config=model.config or GenerateConfig(),
        base_url=default_none(model.base_url),
        api_key=default_none(model.api_key),
        memoize=default(model.memoize, True),
        **_kwargs("model", model.model_args, task),
    )


def _create_model_roles(task: FlowTask, model_roles: ModelRolesConfig) -> ModelRoles:
    roles = {}
    for role, model in model_roles.items():
        if isinstance(model, FlowModel):
            model = _create_model(task=task, model=model)
        roles[role] = model
    return roles


def _create_single_scorer(task: FlowTask, scorer: str | FlowScorer) -> Scorer:
    if isinstance(scorer, str):
        scorer = FlowScorer(name=scorer)
    if not scorer.name:
        raise ValueError(f"Scorer name is required. Scorer: {scorer}")
    return scorer_from_spec(
        ScorerSpec(scorer=scorer.name),
        task_path=None,
        **_kwargs("scorer", scorer.args, task),
    )


def _create_scorer(
    task: FlowTask,
    scorer: str | FlowScorer | Sequence[str | FlowScorer] | None | NotGiven,
) -> Scorer | Sequence[Scorer] | None | InspectNotGiven:
    if isinstance(scorer, NotGiven):
        return NOT_GIVEN
    if scorer is None:
        return None
    if isinstance(scorer, str | FlowScorer):
        return _create_single_scorer(task, scorer)
    return [_create_single_scorer(task, single_solver) for single_solver in scorer]


def _create_single_solver(task: FlowTask, solver: str | FlowSolver) -> Solver:
    if not isinstance(solver, FlowSolver):
        raise ValueError(f"Solver should have been resolved. Solver: {solver}")
    if not solver.name:
        raise ValueError(f"Solver name is required. Solver: {solver}")

    return registry_create(
        type="solver", name=solver.name, **_kwargs("solver", solver.args, task)
    )


def _create_agent(task: FlowTask, agent: FlowAgent) -> Agent:
    if not agent.name:
        raise ValueError(f"Agent name is required. Agent: {agent}")

    return registry_create(
        type="agent", name=agent.name, **_kwargs("agent", agent.args, task)
    )


def _create_solver(
    task: FlowTask,
    solver: FlowSolver | Sequence[str | FlowSolver] | FlowAgent,
) -> SingleSolver:
    if isinstance(solver, FlowSolver):
        return _create_single_solver(task, solver)
    if isinstance(solver, FlowAgent):
        return _create_agent(task, solver)
    return [_create_single_solver(task, single_solver) for single_solver in solver]


def _instantiate_task(spec: FlowSpec, flow_task: str | FlowTask, base_dir: str) -> Task:
    if (
        spec.defaults
        or not isinstance(flow_task, FlowTask)
        or isinstance(flow_task.model, str)
        or isinstance(flow_task.solver, str)
    ):
        raise ValueError("config must be resolved before calling instantiate_task")

    model = _create_model(flow_task, flow_task.model) if flow_task.model else NOT_GIVEN
    scorer = _create_scorer(flow_task, flow_task.scorer)
    solver = (
        _create_solver(flow_task, flow_task.solver) if flow_task.solver else NOT_GIVEN
    )
    model_roles = (
        _create_model_roles(flow_task, flow_task.model_roles)
        if flow_task.model_roles
        else NOT_GIVEN
    )
    task_func = _get_task_creator(flow_task, base_dir=base_dir)
    if model:
        init_active_model(model, model.config)
    task = task_func(**_registry_kwargs(flow_task.args or {}))

    if is_set(flow_task.sample_id):
        task.dataset = slice_dataset(
            task.dataset,
            limit=None,
            sample_id=sequence_to_list(flow_task.sample_id),
        )

    epochs = flow_task.epochs
    if isinstance(epochs, FlowEpochs):
        epochs = Epochs(
            epochs=epochs.epochs,
            reducer=sequence_to_list(epochs.reducer),
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
        scorer=scorer,
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
