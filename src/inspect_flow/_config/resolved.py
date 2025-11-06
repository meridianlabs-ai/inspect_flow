from inspect_ai import Task

from inspect_flow._types.flow_types import FConfig, FTask

def task_to_config(task: Task) -> FTask:
    dict = **(task.__dict__)
    result = 

def config_with_tasks(
    config: FConfig,
    resolved_tasks: list[Task],
) -> FConfig:
    """Return a new FConfig with the provided tasks set."""
    result = config.model_copy(
        update={
            "tasks": [],
            "defaults": None,
        },
    )
    tasks = [task_to_config(task) for task in resolved_tasks]
    return result
