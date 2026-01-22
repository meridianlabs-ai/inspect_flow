from inspect_flow import FlowOptions, FlowSpec, FlowTask
from inspect_flow.api import run

spec = FlowSpec(
    log_dir="logs/model_and_task",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="local_eval/noop",
            model="openai/gpt-4o-mini",
        )
    ],
)

run(spec=spec)
