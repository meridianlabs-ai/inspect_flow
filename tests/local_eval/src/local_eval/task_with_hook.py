from inspect_ai import Task, task, task_with
from inspect_flow import after_instantiate


@task
def hooked_task() -> Task:
    return Task()


@after_instantiate
def tag_with_hooked(tasks: list[Task]) -> list[Task]:
    for t in tasks:
        task_with(t, tags=(t.tags or []) + ["hooked"])
    return tasks
