from typing import Any, TypeAlias, TypeVar

from inspect_ai._util.registry import registry_lookup
from inspect_ai.agent import Agent
from inspect_ai.model import GenerateConfig, Model
from inspect_ai.solver import Solver
from pydantic import BaseModel

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowConfig,
    FlowDefaults,
    FlowModel,
    FlowSolver,
    FlowTask,
    ModelRolesConfig,
)
from inspect_flow._types.merge import merge_recursive
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


def resolve_config(config: FlowConfig) -> FlowConfig:
    resolved_tasks = []
    for task_config in config.tasks or []:
        resolved = _resolve_task(config, task_config)
        resolved_tasks.extend(resolved)

    return config.model_copy(update={"tasks": resolved_tasks, "defaults": None})


def _merge_default(config_dict: dict[str, Any], defaults: BaseModel) -> dict[str, Any]:
    default_dict = defaults.model_dump(mode="json", exclude_none=True)
    return merge_recursive(default_dict, config_dict)


def _merge_defaults(
    config: _T,
    defaults: _T | None,
    prefix_defaults: dict[str, _T] | None,
) -> _T:
    if not defaults and not prefix_defaults:
        return config

    config_dict = config.model_dump(mode="json", exclude_none=True)

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

    return config.__class__.model_validate(config_dict)


def _resolve_model(config: FlowModel, flow_config: FlowConfig) -> FlowModel:
    defaults = flow_config.defaults or FlowDefaults()
    return _merge_defaults(config, defaults.model, defaults.model_prefix)


def _resolve_model_roles(
    config: ModelRolesConfig, flow_config: FlowConfig
) -> ModelRolesConfig:
    roles = {}
    for role, model_config in config.items():
        model = model_config
        if isinstance(model, FlowModel):
            model = _resolve_model(config=model, flow_config=flow_config)
        roles[role] = model
    return roles


def _resolve_single_solver(config: FlowSolver, flow_config: FlowConfig) -> FlowSolver:
    defaults = flow_config.defaults or FlowDefaults()
    return _merge_defaults(config, defaults.solver, defaults.solver_prefix)


def _resolve_agent(config: FlowAgent, flow_config: FlowConfig) -> FlowAgent:
    defaults = flow_config.defaults or FlowDefaults()
    return _merge_defaults(config, defaults.agent, defaults.agent_prefix)


def _resolve_solver(
    config: FlowSolver | list[FlowSolver] | FlowAgent, flow_config: FlowConfig
) -> FlowSolver | list[FlowSolver] | FlowAgent:
    if isinstance(config, FlowSolver):
        return _resolve_single_solver(config, flow_config)
    if isinstance(config, FlowAgent):
        return _resolve_agent(config, flow_config)
    return [
        _resolve_single_solver(single_config, flow_config) for single_config in config
    ]


def _resolve_task(flow_config: FlowConfig, config: FlowTask) -> list[FlowTask]:
    defaults = flow_config.defaults or FlowDefaults()
    config = _merge_defaults(config, defaults.task, defaults.task_prefix)
    model = _resolve_model(config.model, flow_config) if config.model else None
    solver = _resolve_solver(config.solver, flow_config) if config.solver else None
    model_roles = (
        _resolve_model_roles(config.model_roles, flow_config)
        if config.model_roles
        else None
    )
    tasks = []
    for task_func_name in _get_task_creator_names(config):
        generate_config = defaults.config or GenerateConfig()
        if config.config:
            generate_config = generate_config.merge(config.config)
        if model and model.config:
            generate_config = generate_config.merge(model.config)
        task = config.model_copy(
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


def _get_task_creator_names_from_file(file_path: str) -> list[str]:
    file = find_file(file_path)
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


def _get_task_creator_names(config: FlowTask) -> list[str]:
    if not config.name:
        raise ValueError(f"Task name is required. Task: {config}")

    if config.name.find("@") != -1:
        return [config.name]
    if config.name.find(".py") != -1:
        result = _get_task_creator_names_from_file(config.name)
        return result
    else:
        if registry_lookup(type="task", name=config.name):
            return [config.name]
        else:
            # Check if name is a file name
            if file := find_file(config.name):
                return _get_task_creator_names_from_file(file)
            raise LookupError(f"{config.name} was not found in the registry")
