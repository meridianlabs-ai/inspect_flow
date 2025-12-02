from inspect_flow import FlowDependencies, FlowJob, FlowTask

FlowJob(
    dependencies=FlowDependencies(
        dependency_file_mode="auto",  # <1>
        dependency_file="../foo/requirements.txt",  # <2>
        additional_dependencies=["pandas==2.0.0"],  # <3>
        auto_detect_dependencies=True,  # <4>
        use_uv_lock=True,  # <5>
    ),
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-5",
        ),
    ],
)
