import getpass
import subprocess

from inspect_ai.log import EvalLog, ProvenanceData, TagsEdit, edit_eval_log

from inspect_flow._steps.context import mark_dirty
from inspect_flow._types.step import step


def _default_author() -> str:
    try:
        name = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        email = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if name and email:
            return f"{name} <{email}>"
        return name or email
    except (subprocess.CalledProcessError, FileNotFoundError):
        return getpass.getuser()


@step
def tag(
    logs: list[EvalLog],
    *,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> list[EvalLog]:
    """Add or remove tags on eval logs.

    Args:
        logs: EvalLog objects to modify.
        add: Tags to add.
        remove: Tags to remove.
        author: Provenance author. Defaults to git user.
        reason: Reason for the edit.

    Returns:
        Modified EvalLog objects.
    """
    provenance = ProvenanceData(author=author or _default_author(), reason=reason)
    edits = [TagsEdit(tags_add=add or [], tags_remove=remove or [])]
    result = [edit_eval_log(log, edits, provenance) for log in logs]
    mark_dirty(result)
    return result
