from inspect_flow import FlowDependencies, FlowJob, FlowTask

FlowJob(
    dependencies=FlowDependencies(
        dependency_file="../foo/requirements.txt",  # <1>
        additional_dependencies=["pandas==2.0.0"],  # <2>
        auto_detect_dependencies=True,  # <3>
    ),
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-5",
        ),
    ],
)
