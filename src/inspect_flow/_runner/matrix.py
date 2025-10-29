from collections.abc import Callable
from typing import TypeAlias

from inspect_ai import Epochs, Task, task_with
from inspect_ai._eval.task.util import slice_dataset  # TODO:ransom private import
from inspect_ai._util.notgiven import NOT_GIVEN  # TODO:ransom private import
from inspect_ai._util.registry import registry_lookup  # TODO:ransom private import
from inspect_ai.agent import Agent
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.model._model import init_active_model
from inspect_ai.solver import Solver
from inspect_ai.util import registry_create

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

matrix_fields = ["args", "models", "model_roles", "solvers"]


def create_model(model_config: FlowModel) -> Model:
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


def create_model_roles(config: ModelRolesConfig) -> ModelRoles:
    roles = {}
    for role, model_config in config.items():
        model = model_config
        if isinstance(model, FlowModel):
            model = create_model(model_config=model)
        roles[role] = model
    return roles


def create_single_solver(config: FlowSolver) -> Solver:
    return registry_create(type="solver", name=config.name, **(config.args or {}))


def create_solver(
    config: FlowSolver | list[FlowSolver] | FlowAgent,
) -> SingleSolver:
    if isinstance(config, FlowSolver):
        return create_single_solver(config)
    if isinstance(config, FlowAgent):
        return registry_create(type="agent", name=config.name, **(config.args or {}))
    return [create_single_solver(single_config) for single_config in config]


def instantiate_task(flow_config: FlowConfig, config: FlowTask) -> list[Task]:
    model = create_model(config.model) if config.model else None
    solver = create_solver(config.solver) if config.solver else None
    model_roles = create_model_roles(config.model_roles) if config.model_roles else None
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
        if isinstance(epochs, FlowEpochs):
            epochs = Epochs(
                epochs=epochs.epochs,
                reducer=epochs.reducer,
            )

        generate_config = flow_config.config or GenerateConfig()
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


def instantiate_tasks(config: FlowConfig) -> list[Task]:
    return [
        task
        for task_config in config.tasks
        for task in instantiate_task(config, task_config)
    ]


def get_task_creators_from_file(config: FlowTask) -> list[Callable[..., Task]]:
    assert config.file
    file_attr = config.file_attr or config.name
    file = find_file(config.file)
    if not file:
        raise FileNotFoundError(f"File not found: {config.file}")

    module = get_module_from_file(file)
    if file_attr:
        task_funcs = [getattr(module, file_attr)]
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
    return task_funcs


def get_task_creators(config: FlowTask) -> list[Callable[..., Task]]:
    if config.file or config.file_attr:
        config.file = config.file or config.name
        return get_task_creators_from_file(config)
    else:
        registry_name = config.registry_name or config.name
        if not registry_name:
            raise ValueError(
                "registry_name or name not specified for task without file"
            )
        if not registry_lookup(type="task", name=registry_name):
            # Check if name is a file name
            if config.name:
                if file := find_file(config.name):
                    config.file = file
                    config.name = None
                    return get_task_creators_from_file(config)
            raise LookupError(f"{registry_name} was not found in the registry")

        def task_func(**kwargs):
            return registry_create(type="task", name=registry_name, **kwargs)

        task_funcs = [task_func]

    return task_funcs
