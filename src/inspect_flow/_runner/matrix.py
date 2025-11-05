from collections.abc import Callable
from typing import Any, TypeAlias, TypeVar

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.task.util import slice_dataset  # TODO:ransom private import
from inspect_ai._util.notgiven import NOT_GIVEN  # TODO:ransom private import
from inspect_ai._util.registry import registry_lookup  # TODO:ransom private import
from inspect_ai.agent import Agent
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create
from pydantic import BaseModel

from inspect_flow._types.factories import merge_dicts_with_config
from inspect_flow._types.flow_types import (
    FAgent,
    FConfig,
    FDefaults,
    FEpochs,
    FModel,
    FSolver,
    FTask,
    ModelRolesConfig,
)
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]
SingleSolver: TypeAlias = Solver | Agent | list[Solver]

_T = TypeVar("_T", bound=BaseModel)


def merge_default(config_dict: dict[str, Any], defaults: _T) -> dict[str, Any]:
    default_dict = defaults.model_dump(mode="json", exclude_none=True)
    return merge_dicts_with_config(default_dict, config_dict)


def merge_defaults(
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
            config_dict = merge_default(config_dict, vals)

    if defaults:
        config_dict = merge_default(config_dict, defaults)

    return config.__class__.model_validate(config_dict)


def create_model(model_config: FModel, config: FConfig) -> Model:
    defaults = config.defaults or FDefaults()
    model_config = merge_defaults(model_config, defaults.model, defaults.model_prefix)

    return get_model(
        model=model_config.name,
        role=model_config.role,
        default=model_config.default,
        config=model_config.config or GenerateConfig(),
        base_url=model_config.base_url,
        api_key=model_config.api_key,
        memoize=model_config.memoize,
        **(model_config.model_args or {}),
    )


def create_model_roles(config: ModelRolesConfig, flow_config: FConfig) -> ModelRoles:
    roles = {}
    for role, model_config in config.items():
        model = model_config
        if isinstance(model, FModel):
            model = create_model(model_config=model, config=flow_config)
        roles[role] = model
    return roles


def create_single_solver(config: FSolver, flow_config: FConfig) -> Solver:
    defaults = flow_config.defaults or FDefaults()
    config = merge_defaults(config, defaults.solver, defaults.solver_prefix)

    if not config.name:
        raise ValueError(f"Solver name is required. Solver: {config}")

    return registry_create(type="solver", name=config.name, **(config.args or {}))


def create_agent(config: FAgent, flow_config: FConfig) -> Agent:
    defaults = flow_config.defaults or FDefaults()
    config = merge_defaults(config, defaults.agent, defaults.agent_prefix)

    if not config.name:
        raise ValueError(f"Agent name is required. Agent: {config}")

    return registry_create(type="agent", name=config.name, **(config.args or {}))


def create_solver(
    config: FSolver | list[FSolver] | FAgent, flow_config: FConfig
) -> SingleSolver:
    if isinstance(config, FSolver):
        return create_single_solver(config, flow_config)
    if isinstance(config, FAgent):
        return create_agent(config, flow_config)
    return [
        create_single_solver(single_config, flow_config) for single_config in config
    ]


def instantiate_task(flow_config: FConfig, config: FTask) -> list[Task]:
    defaults = flow_config.defaults or FDefaults()
    config = merge_defaults(config, defaults.task, defaults.task_prefix)
    model = create_model(config.model, flow_config) if config.model else None
    solver = create_solver(config.solver, flow_config) if config.solver else None
    model_roles = (
        create_model_roles(config.model_roles, flow_config)
        if config.model_roles
        else None
    )
    tasks = []
    for task_func in get_task_creators(config):
        if model:
            # TODO:ransom avoid calling private API - inspect should support creating tasks with a model
            init_active_model(model, model.config)
        task = task_func(**(config.args or {}))

        if config.sample_id is not None:
            task.dataset = slice_dataset(
                task.dataset,
                limit=None,
                sample_id=config.sample_id,
            )

        epochs = config.epochs
        if isinstance(epochs, FEpochs):
            epochs = Epochs(
                epochs=epochs.epochs,
                reducer=epochs.reducer,
            )

        generate_config = defaults.config or GenerateConfig()
        if config.config:
            generate_config = generate_config.merge(config.config)
        if model:
            generate_config = generate_config.merge(model.config)

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
            config=generate_config,
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


def instantiate_tasks(config: FConfig) -> list[Task]:
    return [
        task
        for task_config in config.tasks
        for task in instantiate_task(config, task_config)
    ]


def get_task_creators_from_file(
    file_path: str, attr: str | None, config: FTask
) -> list[Callable[..., Task]]:
    file = find_file(file_path)
    if not file:
        raise FileNotFoundError(f"File not found: {file_path}")

    module = get_module_from_file(file)
    if attr:
        task_funcs = [getattr(module, attr)]
    else:
        # load all task decorated functions and ensure only one exists
        task_funcs = [
            getattr(module, attr)
            for attr in dir(module)
            if hasattr(getattr(module, attr), "__registry_info__")
            and getattr(module, attr).__registry_info__.type == "task"
        ]
        if not task_funcs:
            raise ValueError("No task functions found in file {file}")
        if len(task_funcs) > 1:
            config.name = None  # Clear the name so it will be set to the name of the attr  # type: ignore
    return task_funcs


def get_task_creators(config: FTask) -> list[Callable[..., Task]]:
    if not config.name:
        raise ValueError(f"Task name is required. Task: {config}")
    config_name = config.name

    if config.name.find("@") != -1:
        file, attr = config.name.split("@", 1)
        return get_task_creators_from_file(file, attr, config)
    if config.name.find(".py") != -1:
        result = get_task_creators_from_file(config.name, None, config)
        return result
    else:
        if not registry_lookup(type="task", name=config.name):
            # Check if name is a file name
            if file := find_file(config.name):
                return get_task_creators_from_file(file, None, config)
            raise LookupError(f"{config.name} was not found in the registry")

        def task_func(**kwargs):
            return registry_create(type="task", name=config_name, **kwargs)

        task_funcs = [task_func]

    return task_funcs
