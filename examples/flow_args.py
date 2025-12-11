from inspect_flow import FlowSpec, FlowTask

all_tasks = [
    FlowTask(name="task_easy", flow_metadata={"priority": 1}),
    FlowTask(name="task_medium", flow_metadata={"priority": 2}),
    FlowTask(name="task_hard", flow_metadata={"priority": 3}),
]


def spec(task_min_priority: int = 1) -> FlowSpec:
    return FlowSpec(
        log_dir="logs",
        tasks=[
            t
            for t in all_tasks
            if (t.flow_metadata or {}).get("priority", 0) >= task_min_priority
        ],
    )
