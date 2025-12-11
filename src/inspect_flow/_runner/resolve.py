import sys
from typing import TypeAlias, TypeVar

from inspect_ai._util.registry import registry_lookup
from inspect_ai.model import Model
from pydantic import BaseModel

from inspect_flow._config.defaults import apply_defaults
from inspect_flow._types.flow_types import (
    FlowSpec,
    FlowTask,
    not_given,
)
from inspect_flow._util.module_util import get_module_from_file
from inspect_flow._util.path_util import find_file

ModelRoles: TypeAlias = dict[str, str | Model]

_T = TypeVar("_T", bound=BaseModel)


def _resolve_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def resolve_spec(spec: FlowSpec, base_dir: str) -> FlowSpec:
    spec = apply_defaults(spec)

    resolved_tasks = []
    for task_config in spec.tasks or []:
        resolved = _resolve_task(task_config, base_dir=base_dir)
        resolved_tasks.extend(resolved)

    return spec.model_copy(
        update={
            "tasks": resolved_tasks,
            "defaults": not_given,
            "python_version": _resolve_python_version(),
        }
    )


def _resolve_task(task: str | FlowTask, base_dir: str) -> list[FlowTask]:
    assert isinstance(
        task, FlowTask
    )  # apply_defaults should have converted str to FlowTask
    names = _get_task_creator_names(task, base_dir=base_dir)
    if names == [task.name]:
        return [task]

    tasks = []
    for task_func_name in names:
        task = task.model_copy(
            update={
                "name": task_func_name,
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
        raise ValueError(f"No task functions found in file {file_path}")
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
            raise LookupError(f"{task.name} was not found in the registry")
