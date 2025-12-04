from inspect_flow import FlowDefaults, FlowJob, FlowModel, FlowTask

FlowJob(
    defaults=FlowDefaults(
        model=FlowModel(name="openai/gpt-4o"),
    ),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model=None,  # Explicitly set to None
        )
    ],
)
# Result: Task uses model=None (overrides the default "openai/gpt-4o")
