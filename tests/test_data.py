from inspect_flow._util.data import read_data, write_data


def test_read_write_roundtrip() -> None:
    assert read_data("key") is None
    write_data("key", "value")
    assert read_data("key") == "value"


def test_write_preserves_existing_keys() -> None:
    write_data("key1", "value1")
    write_data("key2", "value2")
    assert read_data("key1") == "value1"
    assert read_data("key2") == "value2"
