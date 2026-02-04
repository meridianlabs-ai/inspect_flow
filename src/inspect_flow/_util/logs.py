"""Utilities for working with Inspect logs"""

from logging import getLogger

from inspect_ai._util.file import basename, copy_file
from inspect_ai.log import list_eval_logs

from inspect_flow._util.console import path, print
from inspect_flow._util.path_util import path_join

logger = getLogger(__name__)


def copy_all_logs(src_dir: str, dest_dir: str, dry_run: bool) -> None:
    """Copy all log files from src_dir to dest_dir."""
    logs = list_eval_logs(src_dir, recursive=False)
    print(
        f"\n{'Would copy' if dry_run else 'Copying'} logs from {path(src_dir)} to {path(dest_dir)}"
    )
    if not logs:
        print("No logs found", format="info")
    for log_file in logs:
        destination = path_join(dest_dir, basename(log_file.name))
        print(f"{path(log_file.name)}", format="info")
        if not dry_run:
            copy_file(log_file.name, destination)
