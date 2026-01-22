from inspect_ai import Task
from inspect_ai.dataset import example_dataset
from inspect_ai.solver import generate
from inspect_flow import FlowSpec

FlowSpec(
    log_dir="logs",
    tasks=[
        Task(  # <1>
            dataset=example_dataset("security_guide"),
            solver=generate(),
        ),
        "inspect_evals/gpqa_diamond",  # <2>
    ],
)
