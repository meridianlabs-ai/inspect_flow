from pathlib import Path

import pytest
from inspect_ai import Task, task
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._types.flow_types import (
    FlowSpec,
    FlowTask,
)

task_name = "tests/local_eval/src/local_eval/noop.py@noop"  # task from a file relative to the base_dir


def test_file_not_found() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name="missing_file.py"),
        ]
    )
    with pytest.raises(FileNotFoundError) as e:
        resolve_spec(spec=spec, base_dir=".")
    assert "File not found:" in str(e.value)


def test_no_tasks() -> None:
    file = str(Path(__file__).parent / "config" / "e2e_test_flow.py")
    spec = FlowSpec(
        tasks=[
            FlowTask(name=file),
        ]
    )
    with pytest.raises(ValueError) as e:
        resolve_spec(spec=spec, base_dir=".")
    assert "No task functions found in file" in str(e.value)
    assert file in str(e.value)


def test_no_task_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(),
        ]
    )
    with pytest.raises(ValueError) as e:
        resolve_spec(spec=spec, base_dir=".")
    assert "Task name is required." in str(e.value)


def test_unregistered_task_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name="unregistered_task"),
        ]
    )
    with pytest.raises(LookupError) as e:
        resolve_spec(spec=spec, base_dir=".")
    assert "unregistered_task was not found in the registry" in str(e.value)


@task
def noop() -> Task:
    return Task()


def test_registered_task() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name="noop"),
        ]
    )
    spec2 = resolve_spec(spec=spec, base_dir=".")
    assert spec2.tasks
    assert len(spec2.tasks) == 1
    assert spec2.tasks[0]
    assert isinstance(spec2.tasks[0], FlowTask)
    assert spec2.tasks[0].name == "noop"
