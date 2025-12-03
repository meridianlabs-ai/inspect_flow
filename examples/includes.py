from inspect_flow import FlowInclude, FlowJob, FlowTask

FlowJob(
    includes=[
        "defaults.py",
        FlowInclude(config_file_path="../shared.py"),
        FlowInclude(config_file_path="/absolute/path.py"),
    ],
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
        ),
    ],
)
