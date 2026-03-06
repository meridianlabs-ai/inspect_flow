from pathlib import Path

from inspect_ai._util.file import absolute_file_path, filesystem


def strip_trailing_sep(path: str) -> str:
    """Remove trailing separators from a path, preserving the root.

    Matches pathlib behavior: exactly ``//`` is preserved per POSIX,
    any other all-separator path collapses to a single separator.
    """
    fs = filesystem(path)
    stripped = path.rstrip(fs.sep)
    if stripped:
        return stripped
    # All separators — preserve exactly "//" per POSIX, otherwise collapse
    if path == fs.sep * 2:
        return path
    return fs.sep


def absolute_path_relative_to(path: str, base_dir: str) -> str:
    absolute_path = absolute_file_path(path)
    if absolute_path == path:
        # Already an absolute path
        return strip_trailing_sep(absolute_path)

    base_relative_path = Path(base_dir) / path
    return strip_trailing_sep(absolute_file_path(str(base_relative_path)))


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
