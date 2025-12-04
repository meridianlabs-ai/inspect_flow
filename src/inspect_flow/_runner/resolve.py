import sys
from typing import Any, Sequence, TypeAlias, TypeVar

from inspect_ai._util.registry import registry_lookup
from inspect_ai.agent import Agent
from inspect_ai.model import Model
from inspect_ai.solver import Solver
from pydantic import BaseModel

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowDefaults,
    FlowJob,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
    ModelRolesConfig,
    NotGiven,
    not_given,
)
from inspect_flow._types.merge import merge_recursive
from inspect_flow._util.args import MODEL_DUMP_ARGS
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


def _resolve_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def resolve_job(job: FlowJob, base_dir: str) -> FlowJob:
    resolved_tasks = []
    for task_config in job.tasks or []:
        resolved = _resolve_task(job, task_config, base_dir=base_dir)
        resolved_tasks.extend(resolved)

    return job.model_copy(
        update={
            "tasks": resolved_tasks,
            "defaults": not_given,
            "python_version": _resolve_python_version(),
        }
    )


def _merge_default(config_dict: dict[str, Any], defaults: BaseModel) -> dict[str, Any]:
    default_dict = defaults.model_dump(**MODEL_DUMP_ARGS)
    return merge_recursive(default_dict, config_dict)


def _merge_defaults(
    config: _T,
    defaults: _T | None | NotGiven,
    prefix_defaults: dict[str, _T] | None | NotGiven,
) -> _T:
    if not defaults and not prefix_defaults:
        return config

    config_dict = config.model_dump(**MODEL_DUMP_ARGS)

    if prefix_defaults:
        # Filter the prefix defaults to only those that match the config name
        prefix_defaults = {
            prefix: prefix_default
            for prefix, prefix_default in prefix_defaults.items()
            if config_dict.get("name", "").startswith(prefix)
        }
        # Sort prefixes by length descending to match longest prefix first
        prefix_defaults = dict(
            sorted(prefix_defaults.items(), key=lambda item: -len(item[0]))
        )
        for vals in prefix_defaults.values():
            config_dict = _merge_default(config_dict, vals)

    if defaults:
        config_dict = _merge_default(config_dict, defaults)

    return config.__class__.model_validate(config_dict, extra="forbid")


def _resolve_model(model: str | FlowModel, job: FlowJob) -> FlowModel:
    if isinstance(model, str):
        model = FlowModel(name=model)
    defaults = job.defaults or FlowDefaults()
    return _merge_defaults(model, defaults.model, defaults.model_prefix)


def _resolve_model_roles(
    model_roles: ModelRolesConfig, job: FlowJob
) -> ModelRolesConfig:
    roles = {}
    for role, model in model_roles.items():
        if isinstance(model, FlowModel):
            model = _resolve_model(model=model, job=job)
        roles[role] = model
    return roles


def _resolve_single_solver(solver: str | FlowSolver, job: FlowJob) -> FlowSolver:
    if isinstance(solver, str):
        solver = FlowSolver(name=solver)
    defaults = job.defaults or FlowDefaults()
    return _merge_defaults(solver, defaults.solver, defaults.solver_prefix)


def _resolve_agent(agent: FlowAgent, job: FlowJob) -> FlowAgent:
    defaults = job.defaults or FlowDefaults()
    return _merge_defaults(agent, defaults.agent, defaults.agent_prefix)


def _resolve_solver(
    solver: str | FlowSolver | Sequence[str | FlowSolver] | FlowAgent,
    job: FlowJob,
) -> FlowSolver | list[FlowSolver] | FlowAgent:
    if isinstance(solver, str | FlowSolver):
        return _resolve_single_solver(solver, job)
    if isinstance(solver, FlowAgent):
        return _resolve_agent(solver, job)
    return [_resolve_single_solver(single_config, job) for single_config in solver]


def _resolve_task(job: FlowJob, task: str | FlowTask, base_dir: str) -> list[FlowTask]:
    if isinstance(task, str):
        task = FlowTask(name=task)

    defaults = job.defaults or FlowDefaults()
    task = _merge_defaults(task, defaults.task, defaults.task_prefix)
    model = _resolve_model(task.model, job) if task.model else not_given
    solver = _resolve_solver(task.solver, job) if task.solver else not_given
    model_roles = (
        _resolve_model_roles(task.model_roles, job) if task.model_roles else not_given
    )
    generate_config = defaults.config or GenerateConfig()
    if task.config:
        generate_config = generate_config.merge(task.config)
    if model and model.config:
        generate_config = generate_config.merge(model.config)
    if generate_config == GenerateConfig():
        generate_config = not_given
    tasks = []
    for task_func_name in _get_task_creator_names(task, base_dir=base_dir):
        task = task.model_copy(
            update={
                "name": task_func_name,
                "model": model,
                "solver": solver,
                "model_roles": model_roles,
                "config": generate_config,
            }
        )
        tasks.append(task)
    return tasks


def _get_task_creator_names_from_file(file_path: str, base_dir: str) -> list[str]:
    file = find_file(file_path, base_dir=base_dir)
    if not file:
        raise FileNotFoundError(f"File not found: {file_path}")

    module = get_module_from_file(file)
    task_names = [
        f"{file_path}@{attr}"
        for attr in dir(module)
        if hasattr(getattr(module, attr), "__registry_info__")
        and getattr(module, attr).__registry_info__.type == "task"
    ]
    if not task_names:
        raise ValueError("No task functions found in file {file}")
    return task_names


def _get_task_creator_names(task: FlowTask, base_dir: str) -> list[str]:
    if not task.name:
        raise ValueError(f"Task name is required. Task: {task}")

    if task.name.find("@") != -1:
        return [task.name]
    if task.name.find(".py") != -1:
        result = _get_task_creator_names_from_file(task.name, base_dir=base_dir)
        return result
    else:
        if registry_lookup(type="task", name=task.name):
            return [task.name]
        else:
            # Check if name is a file name
            if file := find_file(task.name, base_dir=base_dir):
                return _get_task_creator_names_from_file(file, base_dir=base_dir)
            raise LookupError(f"{task.name} was not found in the registry")
