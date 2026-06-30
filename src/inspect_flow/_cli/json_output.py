import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from typing import Any

import click

from inspect_flow._display.display import (
    get_display,
    get_display_type,
    set_display,
    set_display_type,
)
from inspect_flow._runner.logs import FindLogsResult
from inspect_flow._runner.task_log import TaskLogInfo
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.console import console


@contextmanager
def quiet_output() -> Iterator[None]:
    """Suppress Rich/display output so only JSON is written to stdout."""
    prev_display_type = get_display_type()
    prev_display = get_display()
    prev_quiet = console.quiet
    set_display_type("plain")
    console.quiet = True
    try:
        with redirect_stdout(sys.stderr):
            yield
    finally:
        console.quiet = prev_quiet
        set_display_type(prev_display_type)
        set_display(prev_display)


def ensure_json_supported(spec: FlowSpec) -> None:
    """Raise if --json output is requested for an unsupported execution type."""
    if spec.execution_type == "venv":
        raise click.UsageError(
            "--json is not supported with venv execution because results are "
            "produced in a subprocess. Use the default inproc execution type "
            "(omit --venv), or drop --json."
        )


def emit_json(data: Any) -> None:
    click.echo(json.dumps(data, indent=2, default=str))


def _task_to_json(info: TaskLogInfo) -> dict[str, Any]:
    complete = info.task_samples is not None and info.log_samples >= info.task_samples
    return {
        "name": info.task.name,
        "log_file": info.eval_log.location if info.eval_log else None,
        "samples": info.log_samples,
        "total_samples": info.task_samples,
        "complete": complete,
        "duplicate_logs": list(info.duplicate_logs),
    }


def find_logs_result_to_json(result: FindLogsResult, log_dir: str) -> dict[str, Any]:
    tasks = [_task_to_json(info) for info in result.task_log_info.values()]
    complete = sum(1 for task in tasks if task["complete"])
    return {
        "log_dir": log_dir,
        "tasks": tasks,
        "unrecognized": list(result.unexpected_logs),
        "summary": {
            "total": len(tasks),
            "complete": complete,
            "incomplete": len(tasks) - complete,
        },
    }
