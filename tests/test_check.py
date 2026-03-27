import shutil
from pathlib import Path

from inspect_flow import FlowSpec, FlowTask
from inspect_flow._runner.run import run_eval_set
from inspect_flow.api import check
from rich.console import Console

_TASK = "tests/local_eval/src/local_eval/noop.py@noop"
_NOOP_SAMPLES = 2  # noop task has 2 samples


def test_check_reports_duplicate_logs(
    tmp_path: Path, recording_console: Console
) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )

    run_eval_set(spec=spec, base_dir=".")

    (original,) = Path(log_dir).glob("*.eval")
    shutil.copy(original, original.parent / f"duplicate_{original.name}")

    check(spec=spec, base_dir=".")

    assert "Duplicate logs:" in recording_console.export_text()


def test_check_returns_result_with_no_existing_logs(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    flow_task = FlowTask(name=_TASK, model="mockllm/mock-llm")
    spec = FlowSpec(log_dir=log_dir, tasks=[flow_task])

    result = check(spec=spec, base_dir=".")

    assert result is not None
    assert len(result.tasks) == 1
    assert result.unrecognized == []

    task = result.tasks[0]
    assert task.name == _TASK
    assert task.task.name == flow_task.name
    assert task.log_file is None
    assert task.samples == 0
    assert task.total_samples == _NOOP_SAMPLES
    assert task.duplicate_logs == []


def test_check_returns_result_with_completed_log(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    flow_task = FlowTask(name=_TASK, model="mockllm/mock-llm")
    spec = FlowSpec(log_dir=log_dir, tasks=[flow_task])

    run_eval_set(spec=spec, base_dir=".")
    result = check(spec=spec, base_dir=".")

    assert result is not None
    assert len(result.tasks) == 1
    assert result.unrecognized == []

    task = result.tasks[0]
    assert task.name == _TASK
    assert task.task.name == flow_task.name
    assert task.log_file is not None
    assert task.samples == _NOOP_SAMPLES
    assert task.total_samples == _NOOP_SAMPLES
    assert task.duplicate_logs == []


def test_check_result_task_has_duplicate_logs(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )

    run_eval_set(spec=spec, base_dir=".")

    (original,) = Path(log_dir).glob("*.eval")
    shutil.copy(original, original.parent / f"duplicate_{original.name}")

    result = check(spec=spec, base_dir=".")

    assert result is not None
    assert len(result.tasks[0].duplicate_logs) == 1


def test_check_result_has_unrecognized_logs(tmp_path: Path) -> None:
    log_dir = str(tmp_path / "logs")
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[FlowTask(name=_TASK, model="mockllm/mock-llm")],
    )

    run_eval_set(spec=spec, base_dir=".")

    # Check with a spec that has no tasks — the existing log is unrecognized
    empty_spec = FlowSpec(log_dir=log_dir, tasks=[])
    result = check(spec=empty_spec, base_dir=".")

    assert result is not None
    assert len(result.unrecognized) == 1
    assert result.tasks == []
