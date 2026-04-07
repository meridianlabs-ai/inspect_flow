import json
from datetime import datetime, timezone
from typing import Any


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


def maybe_json(value: str) -> Any:
    """Parse a string as JSON if possible, otherwise return it unchanged."""
    if value == "True":
        return True
    if value == "False":
        return False
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value
