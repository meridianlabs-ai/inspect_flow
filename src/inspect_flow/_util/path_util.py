from pathlib import Path

from fsspec.core import split_protocol
from inspect_ai._util.file import (
    absolute_file_path,
    exists,
    filesystem,
    strip_trailing_sep,
)

AUTO_INCLUDE_FILENAME = "_flow.py"


def absolute_path_relative_to(path: str, base_dir: str) -> str:
    absolute_path = absolute_file_path(path)
    if path.startswith(absolute_path):
        # Already an absolute path
        return absolute_path

    base_relative_path = Path(base_dir) / path
    return absolute_file_path(str(base_relative_path))


def cwd_relative_path(path: str) -> str:
    p = path
    if p.startswith("file://"):
        p = p[7:]
    cwd = Path.cwd().as_posix()
    if len(cwd) > 1 and p.startswith(cwd):
        return p[len(cwd) + 1 :]
    return path


def path_str(path: str) -> str:
    """Return a user friendly string representation of a path"""
    if path.startswith("file://"):
        path = path[7:]
    cwd = Path.cwd().as_posix()
    if len(cwd) > 1 and path.startswith(cwd):
        path = path[len(cwd) + 1 :]
    return path


def find_auto_includes(base_dir: str) -> list[str]:
    """Find _flow.py files in base_dir and all parent directories."""
    protocol, _ = split_protocol(absolute_file_path(base_dir))
    results: list[str] = []
    parent_dir = Path(base_dir)
    while True:
        auto_file = str(parent_dir / AUTO_INCLUDE_FILENAME)
        if protocol:
            auto_file = f"{protocol}://{auto_file}"
        if exists(auto_file):
            results.append(absolute_file_path(auto_file))
        if parent_dir.parent == parent_dir:
            break
        parent_dir = parent_dir.parent
    return results


def path_join(path: str, *paths: str) -> str:
    """Join multiple paths into a single path string."""
    path = strip_trailing_sep(path)
    sep = filesystem(path).sep
    return sep.join([path, *paths])
