from inspect_flow import FlowOptions, FlowSpec, FlowTask


def spec(model: str | None = None) -> FlowSpec:
    return FlowSpec(
        log_dir="logs/model_and_task",
        options=FlowOptions(limit=1),
        tasks=[
            FlowTask(
                name="inspect_evals/mmlu_0_shot",
                model=model or "openai/gpt-4o-mini",
            )
        ],
    )
