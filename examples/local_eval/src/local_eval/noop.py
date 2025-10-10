from inspect_ai import Task, task
from inspect_ai.model import get_model


@task
def noop() -> Task:
    return Task()


@task
def noop2() -> Task:
    return Task()


@task
def task_with_get_model() -> Task:
    _model = get_model()
    return Task()
