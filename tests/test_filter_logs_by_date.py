from datetime import datetime, timezone

from inspect_flow._api.list_logs import _filter_logs_by_date

# Sample log paths with timestamps spanning several days
_JAN_09_LOG = "logs/2026-01-09T18-27-59+00-00_gpqa-diamond_abc.eval"
_JAN_10_MORNING_LOG = "logs/2026-01-10T08-15-00+00-00_gpqa-diamond_def.eval"
_JAN_10_EVENING_LOG = "logs/2026-01-10T22-45-30+00-00_gpqa-diamond_ghi.eval"
_JAN_11_LOG = "logs/2026-01-11T10-00-00+00-00_gpqa-diamond_jkl.eval"
_NO_TS_LOG = "logs/my-custom-log.eval"

_ALL_LOGS = [
    _JAN_09_LOG,
    _JAN_10_MORNING_LOG,
    _JAN_10_EVENING_LOG,
    _JAN_11_LOG,
    _NO_TS_LOG,
]


def test_no_filters_returns_all_timestamped() -> None:
    """With no filters, all timestamped logs pass through (untimestamped are excluded)."""
    result = _filter_logs_by_date(_ALL_LOGS, since=None, until=None)
    assert result == [
        _JAN_09_LOG,
        _JAN_10_MORNING_LOG,
        _JAN_10_EVENING_LOG,
        _JAN_11_LOG,
    ]


def test_since_excludes_older_logs() -> None:
    result = _filter_logs_by_date(_ALL_LOGS, since="2026-01-10", until=None)
    assert _JAN_09_LOG not in result
    assert _JAN_10_MORNING_LOG in result
    assert _JAN_10_EVENING_LOG in result
    assert _JAN_11_LOG in result


def test_until_date_means_midnight() -> None:
    """--until 2026-01-10 means midnight, matching git semantics (exclusive of Jan 10)."""
    result = _filter_logs_by_date(_ALL_LOGS, since=None, until="2026-01-10")
    assert _JAN_09_LOG in result
    assert _JAN_10_MORNING_LOG not in result
    assert _JAN_10_EVENING_LOG not in result
    assert _JAN_11_LOG not in result


def test_since_and_until_same_date() -> None:
    """--since and --until on the same date yields nothing (both resolve to midnight)."""
    result = _filter_logs_by_date(_ALL_LOGS, since="2026-01-10", until="2026-01-10")
    assert result == []


def test_until_with_datetime() -> None:
    cutoff = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    result = _filter_logs_by_date(_ALL_LOGS, since=None, until=cutoff)
    assert _JAN_10_MORNING_LOG in result  # 08:15 < 12:00
    assert _JAN_10_EVENING_LOG not in result  # 22:45 > 12:00


def test_untimestamped_logs_excluded_with_since() -> None:
    """Logs without a filename timestamp should be excluded when --since is set."""
    result = _filter_logs_by_date(_ALL_LOGS, since="2026-01-10", until=None)
    assert _NO_TS_LOG not in result


def test_untimestamped_logs_excluded_with_until() -> None:
    """Logs without a filename timestamp should be excluded when --until is set."""
    result = _filter_logs_by_date(_ALL_LOGS, since=None, until="2026-01-10")
    assert _NO_TS_LOG not in result


def test_untimestamped_logs_excluded_without_filters() -> None:
    """_filter_logs_by_date always excludes untimestamped logs.

    The caller (list_logs) skips this function entirely when no date filters
    are set, so untimestamped logs are preserved in the no-filter path.
    """
    result = _filter_logs_by_date(_ALL_LOGS, since=None, until=None)
    assert _NO_TS_LOG not in result
