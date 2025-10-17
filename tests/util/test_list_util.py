from inspect_flow._util.list_util import (
    ensure_list,
    ensure_list_or_none,
    ensure_non_empty_list,
    flatten,
)


def test_flatten() -> None:
    # Test basic flattening
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

    # Test with empty lists
    assert flatten([]) == []
    assert flatten([[], []]) == []
    assert flatten([[1], [], [2]]) == [1, 2]

    # Test with single nested list
    assert flatten([[1, 2, 3]]) == [1, 2, 3]

    # Test with different data types
    assert flatten([["a", "b"], ["c"]]) == ["a", "b", "c"]
    assert flatten([[1.5, 2.5], [3.5]]) == [1.5, 2.5, 3.5]

    # Test with mixed length sublists
    assert flatten([[1], [2, 3, 4], [5, 6]]) == [1, 2, 3, 4, 5, 6]


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
