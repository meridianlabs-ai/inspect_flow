from dataclasses import dataclass
from typing import Any, Sequence, TypeAlias, TypeVar

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.loader import load_tasks, scorer_from_spec
from inspect_ai._eval.task.util import slice_dataset
from inspect_ai._util.file import filesystem
from inspect_ai._util.notgiven import NOT_GIVEN
from inspect_ai._util.notgiven import NotGiven as InspectNotGiven
from inspect_ai._util.path import chdir_python
from inspect_ai._util.registry import (
    registry_kwargs,
)
from inspect_ai.agent import Agent
from inspect_ai.model import Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.scorer import Scorer
from inspect_ai.scorer._scorer import ScorerSpec
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create
from pydantic import BaseModel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Literal

from inspect_flow._display.display import RunAction
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
from inspect_flow._util.console import console
from inspect_flow._util.list_util import sequence_to_list
from inspect_flow._util.not_given import default, default_none, is_set

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


def _kwargs(
    type: Literal["model", "solver", "scorer", "agent"],
    args: CreateArgs | None | NotGiven,
    task: FlowTask,
) -> dict[str, Any]:
    base_args = args or {}
    additional_args: CreateArgs = (
        task.extra_args and getattr(task.extra_args, type) or {}
    )
    return registry_kwargs(**{**base_args, **additional_args})


@dataclass
class InstantiatedTask:
    flow_task: FlowTask | None
    task: Task


def _get_task_name(task_config: str | FlowTask | Task) -> str:
    if isinstance(task_config, str):
        return task_config
    if isinstance(task_config, FlowTask):
        return task_config.name or "<unnamed>"
    return task_config.name


def instantiate_tasks(spec: FlowSpec, base_dir: str) -> list[InstantiatedTask]:
    task_configs = spec.tasks or []
    if not task_configs:
        return []
    results: list[InstantiatedTask] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.percentage]{task.completed}/{task.total}"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        with RunAction("instantiate", info=progress) as action:
            progress_task = progress.add_task("Instantiating", total=len(task_configs))
            for task_config in task_configs:
                task_name = _get_task_name(task_config)
                progress.update(progress_task, description=f"[cyan]{task_name}[/cyan]")
                for task in _instantiate_task(spec, task_config, base_dir=base_dir):
                    results.append(
                        InstantiatedTask(
                            flow_task=task_config
                            if isinstance(task_config, FlowTask)
                            else None,
                            task=task,
                        )
                    )
                progress.advance(progress_task)
            action.update(info=f"Instantiated {len(results)} tasks")
    return results


def _create_model(task: FlowTask, model: FlowModel | Model) -> Model:
    if isinstance(model, Model):
        return model
    if model.factory:
        return model.factory(**(model.model_args or {}))
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


def _create_single_scorer(task: FlowTask, scorer: str | FlowScorer | Scorer) -> Scorer:
    if isinstance(scorer, Scorer):
        return scorer
    if isinstance(scorer, str):
        scorer = FlowScorer(name=scorer)
    if scorer.factory:
        return scorer.factory(**(scorer.args or {}))
    if not scorer.name:
        raise ValueError(f"Scorer name is required. Scorer: {scorer}")
    return scorer_from_spec(
        ScorerSpec(scorer=scorer.name),
        task_path=None,
        **_kwargs("scorer", scorer.args, task),
    )


def _create_scorer(
    task: FlowTask,
    scorer: str
    | FlowScorer
    | Scorer
    | Sequence[str | FlowScorer | Scorer]
    | None
    | NotGiven,
) -> Scorer | Sequence[Scorer] | None | InspectNotGiven:
    if isinstance(scorer, NotGiven):
        return NOT_GIVEN
    if scorer is None:
        return None
    if isinstance(scorer, Scorer):
        return scorer
    if isinstance(scorer, str | FlowScorer):
        return _create_single_scorer(task, scorer)
    return [_create_single_scorer(task, single_solver) for single_solver in scorer]


def _create_single_solver(task: FlowTask, solver: str | FlowSolver | Solver) -> Solver:
    if isinstance(solver, Solver):
        return solver
    if not isinstance(solver, FlowSolver):
        raise ValueError(f"Solver should have been resolved. Solver: {solver}")
    if solver.factory:
        return solver.factory(**(solver.args or {}))
    if not solver.name:
        raise ValueError(f"Solver name is required. Solver: {solver}")

    return registry_create(
        type="solver", name=solver.name, **_kwargs("solver", solver.args, task)
    )


def _create_agent(task: FlowTask, agent: FlowAgent) -> Agent:
    if agent.factory:
        return agent.factory(**(agent.args or {}))
    if not agent.name:
        raise ValueError(f"Agent name is required. Agent: {agent}")

    return registry_create(
        type="agent", name=agent.name, **_kwargs("agent", agent.args, task)
    )


def _create_solver(
    task: FlowTask,
    solver: FlowSolver
    | Solver
    | FlowAgent
    | Agent
    | Sequence[str | FlowSolver | Solver],
) -> SingleSolver:
    if isinstance(solver, FlowSolver):
        return _create_single_solver(task, solver)
    if isinstance(solver, FlowAgent):
        return _create_agent(task, solver)
    if not isinstance(solver, Sequence):
        return solver
    return [_create_single_solver(task, single_solver) for single_solver in solver]


def _instantiate_task(
    spec: FlowSpec, flow_task: str | FlowTask | Task, base_dir: str
) -> list[Task]:
    if isinstance(flow_task, Task):
        return [flow_task]
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
    if model:
        init_active_model(model, model.config)
    tasks = _create_task(flow_task, base_dir=base_dir)

    for task in tasks:
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
            # name= should be set when loaded
            version=ng(flow_task.version),
            metadata=ng(flow_task.metadata),
        )
    return tasks


def _create_task(task: FlowTask, base_dir: str) -> list[Task]:
    task_args = registry_kwargs(**(task.args or {}))
    # Use factory if provided
    if task.factory:
        return [task.factory(**task_args)]

    if not task.name:
        raise ValueError(f"Task name is required. Task: {task}")

    # Try to create by finding task functions in files
    if filesystem(base_dir).is_local():
        with chdir_python(base_dir):
            tasks = load_tasks(task_specs=[task.name], task_args=task_args)
    else:
        tasks = load_tasks(task_specs=[task.name], task_args=task_args)
    if not tasks:
        raise LookupError(f"No tasks found for name: {task.name}")
    return tasks
