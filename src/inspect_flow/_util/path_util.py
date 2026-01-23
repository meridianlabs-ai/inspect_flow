from pathlib import Path

from inspect_ai._util.file import absolute_file_path


def absolute_path_relative_to(path: str, base_dir: str) -> str:
    absolute_path = absolute_file_path(path)
    if absolute_path == path:
        # Already an absolute path
        return absolute_path

    base_relative_path = Path(base_dir) / path
    return absolute_file_path(str(base_relative_path))
