from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, basename, copy_file, exists
from inspect_ai.log import EvalLog

from inspect_flow._steps.context import read_log, step_context
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


@step
def copy(
    logs: list[EvalLog],
    *,
    dest: str,
    source_prefix: str | None = None,
    overwrite: bool = False,
    store: FlowStore | str | None = None,  # noqa: ARG001 handled by @step wrapper
) -> list[EvalLog]:
    """Copy eval logs to a destination directory.

    Args:
        logs: list of EvalLog to copy.
        dest: Destination directory (local or S3).
        source_prefix: Directory prefix to strip from source paths. Without this option, files are copied flat into the destination. When provided, preserves directory structure relative to the prefix.
        overwrite: Overwrite existing files at the destination.
        store: Optional flow store. The copied log is added to the store.

    Returns:
        EvalLog at the destination location.
    """
    with step_context(logs) as context:
        context.write_dirty()

    dest_paths: list[str] = []
    for log in logs:
        dest_path = dest.rstrip("/") + "/" + _relative_path(log.location, source_prefix)
        if not overwrite and exists(dest_path):
            flow_print(f"Skipping (already exists): {dest_path}", format="warning")
        else:
            copy_file(log.location, dest_path)
        dest_paths.append(dest_path)
    return [read_log(path, header_only=True) for path in dest_paths]
