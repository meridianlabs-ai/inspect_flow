from pathlib import Path

import pytest
from inspect_ai import Task, task
from inspect_flow._runner.resolve import resolve_job
from inspect_flow._types.flow_types import (
    FlowJob,
    FlowTask,
)

task_name = "tests/local_eval/src/local_eval/noop.py@noop"  # task from a file relative to the base_dir


def test_file_not_found() -> None:
    job = FlowJob(
        tasks=[
            FlowTask(name="missing_file.py"),
        ]
    )
    with pytest.raises(FileNotFoundError) as e:
        resolve_job(job=job, base_dir=".")
    assert "File not found:" in str(e.value)


def test_no_tasks() -> None:
    file = str(Path(__file__).parent / "config" / "e2e_test_flow.py")
    job = FlowJob(
        tasks=[
            FlowTask(name=file),
        ]
    )
    with pytest.raises(ValueError) as e:
        resolve_job(job=job, base_dir=".")
    assert "No task functions found in file" in str(e.value)
    assert file in str(e.value)


def test_no_task_name() -> None:
    job = FlowJob(
        tasks=[
            FlowTask(),
        ]
    )
    with pytest.raises(ValueError) as e:
        resolve_job(job=job, base_dir=".")
    assert "Task name is required." in str(e.value)


def test_unregistered_task_name() -> None:
    job = FlowJob(
        tasks=[
            FlowTask(name="unregistered_task"),
        ]
    )
    with pytest.raises(LookupError) as e:
        resolve_job(job=job, base_dir=".")
    assert "unregistered_task was not found in the registry" in str(e.value)


@task
def noop() -> Task:
    return Task()


def test_registered_task() -> None:
    job = FlowJob(
        tasks=[
            FlowTask(name="noop"),
        ]
    )
    job2 = resolve_job(job=job, base_dir=".")
    assert job2.tasks
    assert len(job2.tasks) == 1
    assert job2.tasks[0]
    assert isinstance(job2.tasks[0], FlowTask)
    assert job2.tasks[0].name == "noop"
