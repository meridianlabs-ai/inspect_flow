from datetime import datetime, timezone

import dateparser
from inspect_ai.log import list_eval_logs

from inspect_flow._api.api import ensure_init
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._util.logs import log_filename_ts
from inspect_flow._util.logs import sort_logs as _sort_logs


def _parse_date_arg(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    result: datetime | None = dateparser.parse(
        value, settings={"RETURN_AS_TIMEZONE_AWARE": True}
    )
    if result is None:
        raise ValueError(f"Cannot parse date: {value!r}")
    return result


def _filter_logs_by_date(
    paths: list[str],
    since: str | datetime | None,
    until: str | datetime | None,
) -> list[str]:
    since_dt = _parse_date_arg(since) if since is not None else None
    until_dt = _parse_date_arg(until) if until is not None else None
    filtered: list[str] = []
    for p in paths:
        ts = log_filename_ts(p)
        if ts is None:
            filtered.append(p)
            continue
        if since_dt is not None and ts < since_dt:
            continue
        if until_dt is not None and ts > until_dt:
            continue
        filtered.append(p)
    return filtered


def list_logs(
    log_dir: str | None = None,
    store: str | FlowStore = "auto",
    since: str | datetime | None = None,
    until: str | datetime | None = None,
) -> list[str]:
    """List log paths grouped by directory, directories ordered by most recent log file.

    Within each directory, logs are sorted by filename timestamp descending.
    Logs without a timestamp prefix sort at the end.

    Args:
        log_dir: Directory to list logs from recursively.
            If provided, the store is not used.
        store: The store to read logs from. Can be a `FlowStore` instance,
            a path, or `"auto"` for the default. Only used when `log_dir` is `None`.
        since: Only include logs completed at or after this date. Accepts a
            `datetime` or a date string (e.g. `"2 weeks ago"`, `"2024-01-15"`).
        until: Only include logs completed at or before this date. Accepts a
            `datetime` or a date string (e.g. `"yesterday"`, `"2024-06-01"`).
    """
    ensure_init(dotenv_base_dir=".")
    if log_dir is not None:
        paths = {info.name for info in list_eval_logs(log_dir=log_dir, recursive=True)}
    elif isinstance(store, FlowStore):
        paths = store.get_logs()
    else:
        flow_store = store_factory(store, base_dir=".", create=False, quiet=True)
        paths = flow_store.get_logs() if flow_store else set()
    sorted_paths = _sort_logs(paths)
    if since is None and until is None:
        return sorted_paths
    return _filter_logs_by_date(sorted_paths, since, until)
