from inspect_ai._util.file import basename, dirname
from inspect_ai.log import EvalLog

from inspect_flow._steps.step import step


def _source_prefix(locations: list[str]) -> str:
    dirs = [dirname(loc) for loc in locations]
    parts_list = [d.split("/") for d in dirs]
    common = parts_list[0]
    for parts in parts_list[1:]:
        common = [a for a, b in zip(common, parts, strict=False) if a == b]
    return "/".join(common)


@step(header_only=False)
def copy(
    logs: list[EvalLog], *, dest: str, preserve_structure: bool = False
) -> list[EvalLog]:
    """Copy eval logs to a destination directory.

    Preserves directory structure relative to the common prefix of the
    source paths when preserve_structure is True, otherwise copies flat.

    Args:
        logs: EvalLog objects to copy.
        dest: Destination directory (local or S3).
        preserve_structure: If True, preserves directory structure relative
            to the common prefix of the source paths. Defaults to a flat
            copy using only the filename.

    Returns:
        EvalLog objects at their destination locations.
    """
    prefix = (
        _source_prefix([log.location for log in logs]) if preserve_structure else None
    )
    dest_logs = []
    for log in logs:
        relative = (
            log.location.removeprefix(prefix).lstrip("/")
            if prefix
            else basename(log.location)
        )
        dest_path = dest.rstrip("/") + "/" + relative
        dest_logs.append(log.model_copy(update={"location": dest_path}))
    return dest_logs
