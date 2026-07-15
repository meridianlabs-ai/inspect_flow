from __future__ import annotations

from typing import TYPE_CHECKING

from inspect_flow._steps.step import step

if TYPE_CHECKING:
    from inspect_ai.log import EvalLog


@step
def type_checking_step(logs: list[EvalLog], label: str = "default") -> list[EvalLog]:
    """A step whose annotation imports are guarded by TYPE_CHECKING.

    Args:
        label: A label option.
    """
    return logs
