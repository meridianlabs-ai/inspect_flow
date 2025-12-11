from typing import Any, Sequence, TypeAlias, TypeVar

from inspect_ai.model import Model
from pydantic import BaseModel

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowDefaults,
    FlowModel,
    FlowSolver,
    FlowSpec,
    FlowTask,
    GenerateConfig,
    ModelRolesConfig,
    NotGiven,
    not_given,
)
from inspect_flow._types.merge import merge_recursive
from inspect_flow._util.args import MODEL_DUMP_ARGS

ModelRoles: TypeAlias = dict[str, str | Model]

_T = TypeVar("_T", bound=BaseModel)


def apply_defaults(spec: FlowSpec) -> FlowSpec:
    expanded_tasks = [_apply_task_defaults(spec, task) for task in spec.tasks or []]

    return spec.model_copy(
        update={
            "tasks": expanded_tasks,
            "defaults": not_given,
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


def _apply_model_defaults(model: str | FlowModel, spec: FlowSpec) -> FlowModel:
    if isinstance(model, str):
        model = FlowModel(name=model)
    defaults = spec.defaults or FlowDefaults()
    return _merge_defaults(model, defaults.model, defaults.model_prefix)


def _apply_model_roles_defaults(
    model_roles: ModelRolesConfig, spec: FlowSpec
) -> ModelRolesConfig:
    roles = {}
    for role, model in model_roles.items():
        if isinstance(model, FlowModel):
            model = _apply_model_defaults(model=model, spec=spec)
        roles[role] = model
    return roles


def _apply_single_solver_defaults(
    solver: str | FlowSolver, spec: FlowSpec
) -> FlowSolver:
    if isinstance(solver, str):
        solver = FlowSolver(name=solver)
    defaults = spec.defaults or FlowDefaults()
    return _merge_defaults(solver, defaults.solver, defaults.solver_prefix)


def _apply_agent_defaults(agent: FlowAgent, spec: FlowSpec) -> FlowAgent:
    defaults = spec.defaults or FlowDefaults()
    return _merge_defaults(agent, defaults.agent, defaults.agent_prefix)


def _apply_solver_defaults(
    solver: str | FlowSolver | Sequence[str | FlowSolver] | FlowAgent,
    spec: FlowSpec,
) -> FlowSolver | list[FlowSolver] | FlowAgent:
    if isinstance(solver, str | FlowSolver):
        return _apply_single_solver_defaults(solver, spec)
    if isinstance(solver, FlowAgent):
        return _apply_agent_defaults(solver, spec)
    return [
        _apply_single_solver_defaults(single_config, spec) for single_config in solver
    ]


def _apply_task_defaults(spec: FlowSpec, task: str | FlowTask) -> FlowTask:
    if isinstance(task, str):
        task = FlowTask(name=task)

    defaults = spec.defaults or FlowDefaults()
    task = _merge_defaults(task, defaults.task, defaults.task_prefix)
    model = _apply_model_defaults(task.model, spec) if task.model else not_given
    solver = _apply_solver_defaults(task.solver, spec) if task.solver else not_given
    model_roles = (
        _apply_model_roles_defaults(task.model_roles, spec)
        if task.model_roles
        else not_given
    )
    generate_config = defaults.config or GenerateConfig()
    if task.config:
        generate_config = generate_config.merge(task.config)
    if model and model.config:
        generate_config = generate_config.merge(model.config)
    if generate_config == GenerateConfig():
        generate_config = not_given
    return task.model_copy(
        update={
            "model": model,
            "solver": solver,
            "model_roles": model_roles,
            "config": generate_config,
        }
    )
