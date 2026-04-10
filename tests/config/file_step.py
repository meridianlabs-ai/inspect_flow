from inspect_ai.log import EvalLog, ProvenanceData, TagsEdit, edit_eval_log
from inspect_flow._steps.step import step


@step
def file_step_a(logs: list[EvalLog], label: str = "default") -> list[EvalLog]:
    """A test step loaded from a file.

    Args:
        label: A label to apply as a tag.
    """
    edits = [TagsEdit(tags_add=[label], tags_remove=[])]
    provenance = ProvenanceData(author="test")
    return [edit_eval_log(log, edits, provenance) for log in logs]


@step
def file_step_b(logs: list[EvalLog]) -> list[EvalLog]:
    """Another test step in the same file."""
    return logs
