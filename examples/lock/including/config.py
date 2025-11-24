# Automatically inherits _flow.py
from inspect_flow import FlowJob, FlowOptions, FlowTask

FlowJob(
    log_dir="logs",
    options=FlowOptions(max_samples=32),  # Will raise ValueError!
    tasks=[FlowTask(name="inspect_evals/gpqa_diamond", model="openai/gpt-4o")],
)
