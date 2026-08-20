from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from inspect_flow._display.display import get_display_type, set_display_type
from inspect_flow._types.flow_types import FlowModel, FlowSpec, FlowTask
from inspect_flow.api import eval_set

from tests.test_helpers.log_helpers import init_test_logs


@pytest.fixture(autouse=True)
def reset_initialized() -> Generator[None, None, None]:
    """Reset the _initialized flag so _ensure_init fires each test (and restore the display type that init() sets globally)."""
    from inspect_flow._api import api as api_module

    api_module._initialized = False
    display_type = get_display_type()
    yield
    set_display_type(display_type)


def test_eval_set_runs_spec() -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[
            FlowTask(name="local_eval/noop", model=FlowModel(name="mockllm/mock-llm"))
        ],
    )

    success, logs = eval_set(spec=spec, base_dir=".")

    assert success
    assert len(logs) == 1
    assert logs[0].status == "success"
    # bare boundary call: no flow.yaml is written to the log dir
    assert not (Path(log_dir) / "flow.yaml").exists()


def test_eval_set_maps_options(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[
            FlowTask(name="local_eval/noop", model=FlowModel(name="mockllm/mock-llm"))
        ],
    )

    result = eval_set(spec=spec, base_dir=".")

    assert result == (True, [])
    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    assert len(call_args.kwargs["tasks"]) == 1
    assert call_args.kwargs["retry_on_error"] == 3
    assert call_args.kwargs["max_tasks"] == 10
    assert call_args.kwargs["retry_immediate"] is True


def test_eval_set_requires_log_dir() -> None:
    spec = FlowSpec(tasks=["local_eval/noop"])
    with pytest.raises(ValueError, match="log_dir must be set"):
        eval_set(spec=spec, base_dir=".")
