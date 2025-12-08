from unittest.mock import patch

import pytest
from inspect_flow._util.module_util import (
    execute_src_and_get_last_result,
    get_module_from_file,
)


def test_module_file_not_found() -> None:
    with pytest.raises(FileNotFoundError) as e:
        get_module_from_file("missing_file.py")
    assert "No such file or directory" in str(e.value)
    assert "missing_file.py" in str(e.value)


def test_spec_from_loader_returns_none() -> None:
    """Test that ModuleNotFoundError is raised when spec_from_loader returns None."""
    with patch("inspect_flow._util.module_util.spec_from_loader", return_value=None):
        with pytest.raises(ModuleNotFoundError) as e:
            get_module_from_file(__file__)
        assert "not found" in str(e.value)


def test_no_body() -> None:
    src = ""
    result, g = execute_src_and_get_last_result(src, "test.py", {})
    assert result is None
    assert g["__name__"] == "__main__"
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
