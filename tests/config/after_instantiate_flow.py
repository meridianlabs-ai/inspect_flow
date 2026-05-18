from inspect_ai import Task
from inspect_flow import FlowOptions, FlowSpec, FlowTask, after_instantiate

task_file = "tests/local_eval/src/local_eval/three_tasks.py"


@after_instantiate
def reverse_tasks(tasks: list[Task]) -> list[Task]:
    return list(reversed(tasks))


spec = FlowSpec(
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(name=f"{task_file}@noop1"),
        FlowTask(name=f"{task_file}@noop2"),
        FlowTask(name=f"{task_file}@noop3"),
    ],
)
