"""Utilities for working with Inspect logs"""

from logging import getLogger

from inspect_ai._util.file import basename, copy_file
from inspect_ai.log import list_eval_logs
from rich.text import Text

from inspect_flow._util.console import flow_print, path
from inspect_flow._util.path_util import path_join

logger = getLogger(__name__)


def copy_all_logs(src_dir: str, dest_dir: str, dry_run: bool) -> None:
    """Copy all log files from src_dir to dest_dir."""
    logs = list_eval_logs(src_dir, recursive=False)
    flow_print(
        Text.assemble(
            "\nCopying logs from ",
            path(src_dir),
            " to ",
            path(dest_dir),
        )
    )
    if not logs:
        flow_print("No logs found", format="warning")
    for log_file in logs:
        destination = path_join(dest_dir, basename(log_file.name))
        flow_print(path(log_file.name))
        if not dry_run:
            copy_file(log_file.name, destination)
