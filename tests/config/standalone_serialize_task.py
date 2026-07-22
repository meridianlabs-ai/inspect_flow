from inspect_ai import Task, task
from inspect_ai.dataset import Sample


@task
def standalone_serialize_task() -> Task:
    return Task(dataset=[Sample(id=1, input="hi")])
