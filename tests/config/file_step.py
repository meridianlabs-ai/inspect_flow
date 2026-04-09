from inspect_ai.log import EvalLog, ProvenanceData, TagsEdit, edit_eval_log
from inspect_flow._steps.step import step


@step
def file_step_a(log: EvalLog, label: str = "default") -> EvalLog:
    """A test step loaded from a file.

    Args:
        label: A label to apply as a tag.
    """
    return edit_eval_log(
        log, [TagsEdit(tags_add=[label], tags_remove=[])], ProvenanceData(author="test")
    )


@step
def file_step_b(log: EvalLog) -> EvalLog:
    """Another test step in the same file."""
    return log
