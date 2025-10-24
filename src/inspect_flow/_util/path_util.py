import os
from pathlib import Path

config_path_key = "INSPECT_FLOW_CONFIG_PATH"
cwd_path_key = "INSPECT_FLOW_CWD"


def set_path_env_vars(env: dict[str, str], config_path: str | None) -> None:
    """Set environment variables for config path and cwd."""
    if config_path is not None:
        env[config_path_key] = str(Path(config_path).resolve())
    env[cwd_path_key] = str(Path.cwd().resolve())


def find_file(file_path: str) -> str:
    """Locate a file that may have a path relative to the config file or original cwd."""
    path = Path(file_path)
    if path.exists():
        return str(path.resolve())

    if config_path := os.environ.get("INSPECT_FLOW_CONFIG_PATH"):
        relative_path = Path(config_path).parent / file_path
        if relative_path.exists():
            return str(relative_path.resolve())

    if cwd := os.environ.get("INSPECT_FLOW_CWD"):
        relative_path = Path(cwd) / file_path
        if relative_path.exists():
            return str(relative_path.resolve())

    raise FileNotFoundError(f"File not found: {file_path}")
