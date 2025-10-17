from inspect_flow._util.list_util import (
    ensure_list,
    ensure_list_or_none,
    ensure_non_empty_list,
)


def test_ensure_list() -> None:
    assert ensure_list(None) == []
    assert ensure_list([]) == []
    assert ensure_list([1]) == [1]


def test_ensure_non_empty_list() -> None:
    assert ensure_non_empty_list(None) == [None]
    assert ensure_non_empty_list([]) == [None]
    assert ensure_non_empty_list([1]) == [1]


def test_ensure_list_or_none() -> None:
    assert ensure_list_or_none(None) is None
    assert ensure_list_or_none([]) is None
    assert ensure_list_or_none([1]) == [1]
    assert ensure_list_or_none(1) == [1]
