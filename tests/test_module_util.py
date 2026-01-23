import pytest
from inspect_flow._util.module_util import execute_src_and_get_last_result


def test_no_body() -> None:
    src = ""
    result, g = execute_src_and_get_last_result(src, "test.py", {})
    assert result is None
    assert g["__name__"] == "__flow__"
    assert g["__file__"] == "test.py"


def test_multiple_targets() -> None:
    src = "x = y = 5"
    with pytest.raises(ValueError) as e:
        execute_src_and_get_last_result(src, "test.py", {})
    assert "Only single target assignments" in str(e.value)


def test_no_statement() -> None:
    src = "import pytest"
    result, g = execute_src_and_get_last_result(src, "test.py", {})
    assert result is None
