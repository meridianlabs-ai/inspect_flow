from inspect_flow._util.list_util import (
    ensure_list_or_none,
)


def test_ensure_list_or_none() -> None:
    assert ensure_list_or_none(None) is None
    assert ensure_list_or_none([]) is None
    assert ensure_list_or_none([1]) == [1]
    assert ensure_list_or_none(1) == [1]
