# Automatically inherits _flow.py
from inspect_flow import FlowJob, FlowTask

FlowJob(
    log_dir="logs",
    tasks=[FlowTask(name="inspect_evals/gpqa_diamond", model="openai/gpt-4o")],
)
# Will fail if uncommitted changes exist in the repository
