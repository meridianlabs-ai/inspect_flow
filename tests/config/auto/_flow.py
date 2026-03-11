from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig
from inspect_flow import FlowDefaults, FlowModel, FlowSpec, log_filter


@log_filter
def auto_flow_filter(log: EvalLog) -> bool:
    return log.status == "success"


FlowSpec(
    includes=["_other_flow.py"],
    defaults=FlowDefaults(
        model_prefix={
            "openai": FlowModel(
                base_url="https://api.openai.com/v1/",
                config=GenerateConfig(max_connections=5),
            ),
        }
    ),
)
