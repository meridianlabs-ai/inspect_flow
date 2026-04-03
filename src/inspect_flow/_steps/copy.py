from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, basename, exists
from inspect_ai.log import EvalLog

from inspect_flow._steps.step import step
from inspect_flow._util.console import flow_print


@step(header_only=False)
def copy(
    log: EvalLog,
    *,
    dest: str,
    source_prefix: str | None = None,
    overwrite: bool = False,
) -> EvalLog | None:
    """Copy eval logs to a destination directory.

    Args:
        log: EvalLog to copy.
        dest: Destination directory (local or S3).
        source_prefix: If None, the file is copied flat into the destination.
            When provided, preserves directory structure relative to the prefix.
        overwrite: Overwrite existing files at the destination.

    Returns:
        EvalLog at the destination location.
    """
    if source_prefix:
        _, location = split_protocol(absolute_file_path(log.location))
        _, prefix = split_protocol(absolute_file_path(source_prefix))
        relative = location.removeprefix(prefix).lstrip("/")
    else:
        relative = basename(log.location)
    dest_path = dest.rstrip("/") + "/" + relative
    if not overwrite and exists(dest_path):
        flow_print(f"Skipping (already exists): {dest_path}", format="warning")
        return None
    return log.model_copy(update={"location": dest_path})
