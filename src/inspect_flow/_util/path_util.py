from pathlib import Path

from inspect_ai._util.file import absolute_file_path, filesystem


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


def path_join(path: str, *paths: str) -> str:
    """Join multiple paths into a single path string."""
    sep = filesystem(path).sep
    return sep.join([path, *paths])
