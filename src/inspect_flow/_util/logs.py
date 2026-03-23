"""Utilities for working with Inspect logs"""

import re
from collections.abc import Collection
from datetime import datetime, timezone
from logging import getLogger

from fsspec.core import split_protocol
from inspect_ai._util.file import absolute_file_path, copy_file, filesystem
from inspect_ai.log import (
    EvalLog,
    list_eval_logs,
    read_eval_log_sample_summaries,
    read_eval_log_samples,
)
from rich.text import Text

from inspect_flow._util.console import flow_print, path
from inspect_flow._util.path_util import path_join

_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}[:\-]\d{2}[:\-]\d{2}")

logger = getLogger(__name__)


def log_filename_ts(path: str) -> datetime | None:
    """Extract the timestamp from a log filename, or None if absent."""
    m = _TIMESTAMP_RE.search(path.rsplit("/", 1)[-1])
    if not m:
        return None
    # Filenames use dashes as time separators (HH-MM-SS); normalise to colons.
    ts_str = m.group(0)
    date_part, time_part = ts_str.split("T", 1)
    normalised = f"{date_part}T{time_part.replace('-', ':')}"
    return datetime.fromisoformat(normalised).replace(tzinfo=timezone.utc)


def sort_logs(log_paths: Collection[str]) -> list[str]:
    """Sort logs grouped by directory, directories ordered by most recent log file.

    Within each directory, logs are sorted by filename timestamp descending.
    Logs without a timestamp prefix sort at the end.
    """
    return [p for group in group_logs_by_dir(log_paths) for p in group]


def group_logs_by_dir(log_paths: Collection[str]) -> list[list[str]]:
    """Group logs by directory, directories ordered by most recent log file.

    Within each directory, logs are sorted by filename timestamp descending.
    Logs without a timestamp prefix sort at the end.
    """
    groups: dict[str, list[str]] = {}
    for log_path in log_paths:
        dir_path = log_path.rsplit("/", 1)[0] if "/" in log_path else ""
        groups.setdefault(dir_path, []).append(log_path)

    sorted_groups = [_sort_within_dir(paths) for paths in groups.values()]

    ts_groups: list[list[str]] = []
    non_ts_groups: list[list[str]] = []
    for group in sorted_groups:
        if _TIMESTAMP_RE.match(group[0].rsplit("/", 1)[-1]):
            ts_groups.append(group)
        else:
            non_ts_groups.append(group)

    ts_groups.sort(key=lambda g: g[0].rsplit("/", 1)[-1], reverse=True)
    non_ts_groups.sort(key=lambda g: g[0].rsplit("/", 1)[-1])
    return ts_groups + non_ts_groups


def _sort_within_dir(logs: Collection[str]) -> list[str]:
    with_ts: list[str] = []
    without_ts: list[str] = []
    for log in logs:
        basename = log.rsplit("/", 1)[-1]
        if _TIMESTAMP_RE.match(basename):
            with_ts.append(log)
        else:
            without_ts.append(log)
    with_ts.sort(key=lambda p: p.rsplit("/", 1)[-1], reverse=True)
    without_ts.sort(key=lambda p: p.rsplit("/", 1)[-1])
    return with_ts + without_ts


def copy_all_logs(src_dir: str, dest_dir: str, dry_run: bool, recursive: bool) -> None:
    """Copy all log files from src_dir to dest_dir, preserving directory structure.

    Args:
        src_dir: Source directory containing log files.
        dest_dir: Destination directory to copy log files to.
        dry_run: If True, preview what would be copied without making changes.
        recursive: If True, search src_dir recursively for log files.
    """
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
    _, prefix = split_protocol(absolute_file_path(src_dir).rstrip(sep) + sep)
    for log_file in logs:
        _, log_path = split_protocol(log_file.name)
        if not log_path.startswith(prefix):
            raise ValueError(f"Log {log_file.name} is not under {src_dir}")
        relative = log_path[len(prefix) :]
        destination = path_join(dest_dir, relative)
        flow_print(path(log_file.name))
        if not dry_run:
            copy_file(log_file.name, destination)


def num_valid_samples(header: EvalLog) -> int:
    if header.results and not header.invalidated:
        return header.results.completed_samples
    if header.invalidated:
        return sum(
            1
            for s in read_eval_log_samples(header.location)
            if s.invalidation is None and s.error is None
        )
    else:
        return sum(
            1 for s in read_eval_log_sample_summaries(header.location) if s.completed
        )
