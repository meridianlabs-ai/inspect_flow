# Pass Task objects directly to FlowSpec.tasks
# Use this when you don't need to override task parameters
from inspect_ai import Task, task
from inspect_ai.dataset import example_dataset
from inspect_ai.solver import generate
from inspect_flow import FlowSpec


@task  # Optional: use @task decorator to make function available in the registry
def my_custom_task():
    return Task(
        dataset=example_dataset("security_guide"),
        solver=generate(),
    )


FlowSpec(
    log_dir="logs",
    tasks=[
        my_custom_task(),
        "inspect_evals/gpqa_diamond",
    ],
)
