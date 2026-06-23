import json
from pathlib import Path
from typing import Any

import platformdirs

from inspect_flow._util.constants import PKG_NAME

_DATA_FILE = "flow_data.json"

LAST_LOG_DIR_KEY = "last_log_dir"


def user_data_dir() -> Path:
    return Path(platformdirs.user_data_dir(PKG_NAME))


def _data_path() -> Path:
    return user_data_dir() / _DATA_FILE


def read_data(key: str) -> Any:
    """Read a value from the persistent flow data file.

    Args:
        key: The key to read.

    Returns:
        The value, or None if the key is not found or the file does not exist.
    """
    path = _data_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data.get(key)


def write_data(key: str, value: Any) -> None:
    """Write a value to the persistent flow data file.

    Args:
        key: The key to write.
        value: The value to write.
    """
    path = _data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.exists():
        data = json.loads(path.read_text())
    data[key] = value
    path.write_text(json.dumps(data, indent=2) + "\n")
