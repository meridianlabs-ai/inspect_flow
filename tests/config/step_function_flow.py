from inspect_ai.log import EvalLog
from inspect_flow._steps.step import step


@step
def my_step(log: EvalLog) -> EvalLog:
    return log
