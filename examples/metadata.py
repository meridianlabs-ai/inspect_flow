from inspect_flow import FlowOptions, FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
    options=FlowOptions(
        metadata={
            "experiment": "baseline_v1",
            "hypothesis": "Higher temperature improves creative tasks",
            "hardware": "A100-80GB",
        }
    ),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
            metadata={
                "task_variant": "chemistry_subset",
                "note": "Testing with reduced context",
            },
        )
    ],
)
