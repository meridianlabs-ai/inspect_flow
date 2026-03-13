from inspect_ai.log import EvalLog, ProvenanceData, TagsEdit, edit_eval_log

from inspect_flow._types.step import step


@step
def tag(
    logs: list[EvalLog],
    *,
    tags_add: list[str] | None = None,
    tags_remove: list[str] | None = None,
    provenance: ProvenanceData,
) -> list[EvalLog]:
    """Add or remove tags on eval logs in-memory.

    Args:
        logs: EvalLog objects to modify.
        tags_add: Tags to add.
        tags_remove: Tags to remove.
        provenance: Provenance data for the edit.

    Returns:
        Modified EvalLog objects (not persisted to disk).
    """
    edits = [TagsEdit(tags_add=tags_add or [], tags_remove=tags_remove or [])]
    return [edit_eval_log(log, edits, provenance) for log in logs]
