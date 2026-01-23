from defaults_flow import spec as included_spec
from inspect_flow import FlowSpec, FlowTask

spec = FlowSpec(
    includes=[included_spec],
    log_dir="./logs/python_import_flow",
    tasks=[
        FlowTask(
            name="local_eval/noop",
            model="openai/gpt-4o-mini",
        )
    ],
)
