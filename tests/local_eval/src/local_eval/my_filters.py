from inspect_ai.log import EvalLog
from inspect_flow import log_filter


@log_filter
def only_success(log: EvalLog) -> bool:
    return log.status == "success"


@log_filter
def only_anthropic(log: EvalLog) -> bool:
    return log.eval.model.startswith("anthropic")
