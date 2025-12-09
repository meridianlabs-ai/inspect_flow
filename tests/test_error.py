import sys

import pytest
from inspect_flow._util import error
from inspect_flow._util.error import set_exception_hook


@pytest.fixture(autouse=True)
def restore_exception_hook():
    """Fixture to save and restore sys.excepthook and the global flag."""
    # Save original state
    original_hook = sys.excepthook
    original_flag = error._exception_hook_set

    yield

    # Restore original state after test
    sys.excepthook = original_hook
    error._exception_hook_set = original_flag


def test_set_exception_hook_is_idempotent():
    """Test that calling set_exception_hook multiple times only sets it once."""
    set_exception_hook()
    first_hook = sys.excepthook

    # Call again
    set_exception_hook()
    second_hook = sys.excepthook

    # Should be the same hook (not replaced)
    assert first_hook is second_hook


def test_exception_hook_handles_flow_handled_exceptions():
    """Test that the custom hook exits without printing for _flow_handled exceptions."""
    set_exception_hook()

    # Create an exception with _flow_handled flag
    exc = Exception("test")
    exc._flow_handled = True  # type: ignore[attr-defined]

    # The hook should call sys.exit, so we need to catch it
    with pytest.raises(SystemExit) as exc_info:
        sys.excepthook(type(exc), exc, None)  # type: ignore[arg-type]

    assert exc_info.value.code == 1


def test_exception_hook_handles_called_process_error():
    """Test that CalledProcessError exits with its returncode."""
    import subprocess

    set_exception_hook()

    exc = subprocess.CalledProcessError(42, "test_cmd")

    with pytest.raises(SystemExit) as exc_info:
        sys.excepthook(type(exc), exc, None)

    assert exc_info.value.code == 42


def test_exception_hook_handles_other_exceptions(capsys):
    """Test that the custom hook logs and exits for other exceptions."""
    set_exception_hook()

    exc = Exception("test")

    sys.excepthook(type(exc), exc, None)

    assert "Exception: test" in capsys.readouterr().err
