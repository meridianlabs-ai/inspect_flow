from pathlib import Path

import pytest
from inspect_flow._util.module_util import (
    execute_file_and_get_last_result,
    execute_src_and_get_last_result,
)


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


def test_plain_function_called() -> None:
    path = str(Path(__file__).parent / "config" / "plain_function_flow.py")
    result, _ = execute_file_and_get_last_result(path, {})
    assert result == {"name": "default"}


def test_plain_function_called_with_args() -> None:
    path = str(Path(__file__).parent / "config" / "plain_function_flow.py")
    result, _ = execute_file_and_get_last_result(path, {"name": "custom"})
    assert result == {"name": "custom"}


def test_step_function_not_called() -> None:
    path = str(Path(__file__).parent / "config" / "step_function_flow.py")
    result, g = execute_file_and_get_last_result(path, {})
    assert result is None
    assert callable(g["my_step"])
