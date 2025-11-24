import os
from pathlib import Path

from inspect_ai._util.file import absolute_file_path


def find_file(file_path: str, base_dir: str) -> str | None:
    path = Path(file_path)
    if path.exists():
        return str(path.resolve())

    relative_path = Path(base_dir) / file_path
    if relative_path.exists():
        return str(relative_path.resolve())

    return None


def absolute_path_relative_to(path: str, base_path: str) -> str:
    absolute_path = absolute_file_path(path)
    if absolute_path == path:
        # Already an absolute path
        return absolute_path

    base_relative_path = Path(base_path) / path
    return absolute_file_path(str(base_relative_path))


def absolute_path(path: str) -> str:
    absolute_path = absolute_file_path(path)
    if absolute_path == path:
        # Already an absolute path
        return absolute_path

    # Resolve relative path based on config path if set
    if config_path := os.environ.get("INSPECT_FLOW_CONFIG_PATH"):
        config_relative_path = Path(config_path).parent / path
        return absolute_file_path(str(config_relative_path))

    # Resolve relative path based on cwd
    return absolute_path
