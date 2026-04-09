import getpass
import subprocess
from typing import Any

from inspect_ai.log import (
    EvalLog,
    MetadataEdit,
    ProvenanceData,
    TagsEdit,
    edit_eval_log,
)

from inspect_flow._steps.step import step


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
    log: EvalLog,
    *,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> EvalLog:
    """Add or remove tags on eval logs.

    Args:
        log: EvalLog to modify.
        add: Tags to add.
        remove: Tags to remove.
        author: Provenance author. Defaults to git user.
        reason: Reason for the edit.

    Returns:
        Modified EvalLog objects.
    """
    if not add and not remove:
        raise ValueError("At least one of 'add' or 'remove' must be provided.")
    provenance = ProvenanceData(author=author or _default_author(), reason=reason)
    edits = [TagsEdit(tags_add=add or [], tags_remove=remove or [])]
    return edit_eval_log(log, edits, provenance)


@step
def metadata(
    log: EvalLog,
    *,
    set: dict[str, Any] | None = None,
    remove: list[str] | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> EvalLog:
    """Set or delete metadata fields on eval logs.

    Args:
        log: EvalLog object to modify.
        set: Key-value pairs to set.
        remove: Keys to delete.
        author: Provenance author. Defaults to git user.
        reason: Reason for the edit.

    Returns:
        Modified EvalLog object.
    """
    if not set and not remove:
        raise ValueError("At least one of 'set' or 'remove' must be provided.")
    provenance = ProvenanceData(author=author or _default_author(), reason=reason)
    edits = [MetadataEdit(metadata_set=set or {}, metadata_remove=remove or [])]
    return edit_eval_log(log, edits, provenance)
