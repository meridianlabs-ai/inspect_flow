"""Utilities for working with Inspect logs"""

from logging import getLogger

from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, copy_file, filesystem
from inspect_ai.log import list_eval_logs
from rich.text import Text

from inspect_flow._util.console import flow_print, path
from inspect_flow._util.path_util import path_join

logger = getLogger(__name__)


def copy_all_logs(src_dir: str, dest_dir: str, dry_run: bool, recursive: bool) -> None:
    """Copy all log files from src_dir to dest_dir."""
    logs = list_eval_logs(src_dir, recursive=recursive)
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
    sep = filesystem(src_dir).sep
    prefix = absolute_file_path(src_dir).rstrip(sep) + sep
    for log_file in logs:
        _, log_path = split_protocol(log_file.name)
        if not log_path.startswith(prefix):
            raise ValueError(f"Log {log_file.name} is not under {src_dir}")
        relative = log_path[len(prefix) :]
        destination = path_join(dest_dir, relative)
        flow_print(path(log_file.name))
        if not dry_run:
            copy_file(log_file.name, destination)
