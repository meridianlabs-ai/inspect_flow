from inspect_ai import Task, task


@task
def noop1() -> Task:
    return Task()


@task
def noop2() -> Task:
    return Task()


@task
def noop3() -> Task:
    return Task()


def undecorated_task() -> Task:
    return Task()
