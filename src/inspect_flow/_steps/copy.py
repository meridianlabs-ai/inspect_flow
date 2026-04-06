from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, basename, exists
from inspect_ai.log import EvalLog

from inspect_flow._steps.step import step
from inspect_flow._store.store import FlowStore
from inspect_flow._util.console import flow_print


def _relative_path(location: str, source_prefix: str | None) -> str:
    """Return the relative portion of location for the destination."""
    if source_prefix:
        _, abs_location = split_protocol(absolute_file_path(location))
        _, abs_prefix = split_protocol(absolute_file_path(source_prefix))
        if abs_location.startswith(abs_prefix):
            return abs_location.removeprefix(abs_prefix).lstrip("/")
    return basename(location)


@step(header_only=False)
def copy(
    log: EvalLog,
    *,
    dest: str,
    source_prefix: str | None = None,
    overwrite: bool = False,
    store: FlowStore | None = None,
) -> EvalLog | None:
    """Copy eval logs to a destination directory.

    Args:
        log: EvalLog to copy.
        dest: Destination directory (local or S3).
        source_prefix: Directory prefix to strip from source paths. Without this option, files are copied flat into the destination. When provided, preserves directory structure relative to the prefix.
        overwrite: Overwrite existing files at the destination.
        store: Optional flow store. The copied log is added to the store.

    Returns:
        EvalLog at the destination location.
    """
    dest_path = dest.rstrip("/") + "/" + _relative_path(log.location, source_prefix)
    if not overwrite and exists(dest_path):
        flow_print(f"Skipping (already exists): {dest_path}", format="warning")
        return None
    return log.model_copy(update={"location": dest_path})
