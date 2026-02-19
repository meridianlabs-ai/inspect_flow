from inspect_flow import FlowSpec, FlowTask

FlowSpec(  # <1>
    log_dir="project-1",  # <1>
    tasks=[  # <1>
        FlowTask(  # <1>
            name="inspect_evals/gpqa_diamond",  # <1>
            model="openai/gpt-4o",  # <1>
        )  # <1>
    ],  # <1>
)  # <1>
