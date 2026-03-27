import shutil
from pathlib import Path

from inspect_flow import FlowSpec, FlowTask
from inspect_flow._runner.run import run_eval_set
from inspect_flow.api import check
from rich.console import Console

_TASK = "tests/local_eval/src/local_eval/noop.py@noop"


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
