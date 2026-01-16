import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from inspect_flow import FlowAgent, FlowSpec, FlowTask
from inspect_flow._types.flow_types import FlowExtraArgs

from .agentic import simple_tool

FlowSpec(
    log_dir="simple-tool-logs",
    tasks=[
        FlowTask(
            name="./agentic.py@cyber_ctf_task",
            solver=FlowAgent(name="local_eval/simple_agent"),
            model="openai/gpt-4o-mini",
            extra_args=FlowExtraArgs(
                agent={
                    "tools": [
                        simple_tool(),
                    ],
                },
            ),
        ),
    ],
)
