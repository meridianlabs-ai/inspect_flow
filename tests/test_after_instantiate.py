from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from inspect_ai import Task
from inspect_ai._util.registry import _registry
from inspect_flow import (
    FlowOptions,
    FlowSpec,
    FlowTask,
    after_instantiate,
)
from inspect_flow._api.api import load_spec
from inspect_flow._config.load import ConfigOptions, expand_spec
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.after_instantiate import (
    AFTER_INSTANTIATE_TYPE,
    registered_after_instantiate_hooks,
    run_after_instantiate_hooks,
)
from inspect_flow._types.flow_types import FlowInternal

from .test_helpers.log_helpers import init_test_logs

config_dir = str(Path(__file__).parent / "config")
task_file = "tests/local_eval/src/local_eval/three_tasks.py"


@pytest.fixture(autouse=True)
def clean_after_instantiate_registry() -> Generator[None, None, None]:
    """Remove `@after_instantiate`-registered hooks before and after each test
    so registrations from one test don't leak into the next."""
    prefix = f"{AFTER_INSTANTIATE_TYPE}:"
    for key in [k for k in _registry if k.startswith(prefix)]:
        del _registry[key]
    yield
    for key in [k for k in _registry if k.startswith(prefix)]:
        del _registry[key]


def test_decorator_registers_in_registry() -> None:
    @after_instantiate
    def my_hook(tasks: list[Task]) -> list[Task]:
        return tasks

    assert my_hook in registered_after_instantiate_hooks()


def test_run_hooks_applies_returned_list() -> None:
    a, b, c = Task(name="a"), Task(name="b"), Task(name="c")

    @after_instantiate
    def reverse(tasks: list[Task]) -> list[Task]:
        return list(reversed(tasks))

    result = run_after_instantiate_hooks([a, b, c])
    assert result == [c, b, a]


def test_run_hooks_none_return_keeps_list() -> None:
    a, b = Task(name="a"), Task(name="b")
    calls: list[list[Task]] = []

    @after_instantiate
    def in_place(tasks: list[Task]) -> None:
        calls.append(tasks)
        return None

    result = run_after_instantiate_hooks([a, b])
    assert result == [a, b]
    assert calls == [[a, b]]


def test_multiple_hooks_run_in_alphabetical_order() -> None:
    order: list[str] = []

    @after_instantiate
    def b_second(tasks: list[Task]) -> None:
        order.append("b")

    @after_instantiate
    def a_first(tasks: list[Task]) -> None:
        order.append("a")

    run_after_instantiate_hooks([])
    assert order == ["a", "b"]


def test_loader_populates_python_files() -> None:
    spec = load_spec(str(Path(config_dir) / "after_instantiate_flow.py"))
    assert isinstance(spec.internal, FlowInternal)
    files = spec.internal.python_files
    assert isinstance(files, list)
    assert any(f.endswith("after_instantiate_flow.py") for f in files)


def test_loader_omits_internal_when_no_hooks() -> None:
    spec = load_spec(str(Path(config_dir) / "default_config_flow.py"))
    # No @after_instantiate in this config — internal stays not-given
    assert not isinstance(spec.internal, FlowInternal)


def test_run_eval_set_invokes_hook(mock_eval_set: MagicMock) -> None:
    log_dir = init_test_logs()
    spec = load_spec(str(Path(config_dir) / "after_instantiate_flow.py"))
    spec = expand_spec(
        spec,
        base_dir=config_dir,
        options=ConfigOptions(overrides=[f"log_dir={log_dir}"]),
    )
    run_eval_set(spec=spec, base_dir=".")

    mock_eval_set.assert_called_once()
    tasks_arg = mock_eval_set.call_args.kwargs["tasks"]
    names = [t.name.rsplit("@", 1)[-1] for t in tasks_arg]
    # config registered three tasks (noop1, noop2, noop3); hook reverses them
    assert names == ["noop3", "noop2", "noop1"]


def test_bridge_loads_hook_file_into_registry() -> None:
    # Simulates the venv child: registry starts empty for after_instantiate;
    # bridge file load registers the hook.
    assert registered_after_instantiate_hooks() == []
    spec = FlowSpec(
        log_dir="example_logs",
        internal=FlowInternal(
            python_files=[str(Path(config_dir) / "after_instantiate_flow.py")]
        ),
    )
    from inspect_flow._runner.run import _load_internal_python_files

    _load_internal_python_files(spec)
    hooks = registered_after_instantiate_hooks()
    assert len(hooks) == 1
    assert hooks[0].__name__ == "reverse_tasks"


def test_inproc_hook_in_flow_task_module(mock_eval_set: MagicMock) -> None:
    # A @after_instantiate in a task module file is discovered via the
    # registry without any bridge entry — load_tasks loads the file as a side
    # effect of instantiation, and the decorator fires there.
    log_dir = init_test_logs()
    hook_task_file = "tests/local_eval/src/local_eval/task_with_hook.py"
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=f"{hook_task_file}@hooked_task")],
        options=FlowOptions(limit=1),
    )
    run_eval_set(spec=spec, base_dir=".")

    mock_eval_set.assert_called_once()
    tasks_arg = mock_eval_set.call_args.kwargs["tasks"]
    # The hook in task_with_hook.py adds a tag to each task; assert it ran.
    assert all("hooked" in (t.tags or []) for t in tasks_arg)
