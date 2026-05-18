from collections.abc import Callable
from typing import TypeAlias, cast

from inspect_ai import Task
from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_find,
    registry_info,
    registry_name,
)

AfterInstantiate: TypeAlias = Callable[[list[Task]], list[Task] | None]

AFTER_INSTANTIATE_TYPE = "after_instantiate"

INSPECT_FLOW_AFTER_INSTANTIATE_ATTR = "_inspect_flow_after_instantiate"


def after_instantiate(func: AfterInstantiate) -> AfterInstantiate:
    """Decorator to register a function to run after tasks are instantiated.

    The decorated function receives the list of instantiated `Task` objects
    and may either return a new list (replacing the tasks that `eval_set`
    sees) or return `None` to keep the list it was given (after any in-place
    edits).

    All registered hooks fire on every run, in alphabetical order by
    registered name. Hooks defined in any source reachable by spec loading or
    task instantiation are discovered automatically — including spec files,
    `_flow.py` auto-includes, task modules loaded by path, and entry-point
    packages installed in the venv.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    name = registry_name(func, func.__name__)
    # model_construct bypasses Pydantic literal validation of RegistryType,
    # since "after_instantiate" is not in inspect_ai's RegistryType enum.
    registry_add(
        func,
        RegistryInfo.model_construct(type=AFTER_INSTANTIATE_TYPE, name=name),
    )
    setattr(func, INSPECT_FLOW_AFTER_INSTANTIATE_ATTR, True)
    return func


def registered_after_instantiate_hooks() -> list[AfterInstantiate]:
    """Return all registered `@after_instantiate` hooks, sorted by name."""
    hooks = registry_find(lambda info: info.type == AFTER_INSTANTIATE_TYPE)
    sorted_hooks = sorted(hooks, key=lambda fn: registry_info(fn).name)
    return [cast(AfterInstantiate, fn) for fn in sorted_hooks]


def run_after_instantiate_hooks(tasks: list[Task]) -> list[Task]:
    """Run all registered `@after_instantiate` hooks against `tasks`.

    Hooks run in alphabetical order by registered name. Each hook receives the
    output of the previous one (or the unchanged list, if the previous hook
    returned `None`).
    """
    for hook in registered_after_instantiate_hooks():
        result = hook(tasks)
        if result is not None:
            tasks = result
    return tasks
