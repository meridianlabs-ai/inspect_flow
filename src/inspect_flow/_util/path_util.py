import os
from pathlib import Path

from inspect_ai._util.file import absolute_file_path

config_path_key = "INSPECT_FLOW_CONFIG_PATH"
cwd_path_key = "INSPECT_FLOW_CWD"


def set_config_path_env_var(config_path: str) -> None:
    os.environ[config_path_key] = str(Path(config_path).resolve())


def set_cwd_env_var() -> None:
    os.environ[cwd_path_key] = str(Path.cwd().resolve())


def find_file(file_path: str) -> str | None:
    """Locate a file that may have a path relative to the config file or original cwd."""
    path = Path(file_path)
    if path.exists():
        return str(path.resolve())

    if config_path := os.environ.get(config_path_key):
        relative_path = Path(config_path).parent / file_path
        if relative_path.exists():
            return str(relative_path.resolve())

    if cwd := os.environ.get(cwd_path_key):
        relative_path = Path(cwd) / file_path
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
