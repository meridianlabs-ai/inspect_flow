from inspect_flow import FlowOptions, FlowSpec, FlowTask

FlowSpec(
    options=FlowOptions(limit=1),
    tasks=[FlowTask(name="inspect_evals/mmlu_0_shot", model="openai/gpt-4o-mini")],
)
