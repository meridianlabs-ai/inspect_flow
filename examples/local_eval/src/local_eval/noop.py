from inspect_ai import Task, task


@task
def noop() -> Task:
    """Creates a no-op task that does nothing."""
    return Task()
