from inspect_ai._util.file import basename
from inspect_ai.log import EvalLog

from inspect_flow._steps.step import step


@step(header_only=False)
def copy(log: EvalLog, *, dest: str, source_prefix: str | None = None) -> EvalLog:
    """Copy an eval log to a destination directory.

    Args:
        log: EvalLog to copy.
        dest: Destination directory (local or S3).
        source_prefix: If None, the file is copied flat into the destination.
            When provided, preserves directory structure relative to the prefix.

    Returns:
        EvalLog at the destination location.
    """
    relative = (
        log.location.removeprefix(source_prefix).lstrip("/")
        if source_prefix
        else basename(log.location)
    )
    dest_path = dest.rstrip("/") + "/" + relative
    return log.model_copy(update={"location": dest_path})
