from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from inspect_ai import Task
from inspect_ai._util.registry import registry_info
from rich.table import Table
from rich.text import Text

from inspect_flow._types.flow_types import (
    FlowTask,
    NotGiven,
)
from inspect_flow._util.console import quantity
from inspect_flow._util.path_util import path_str


@dataclass
class TaskLogInfo:
    task: Task
    flow_task: FlowTask | None = None
    task_samples: int | None = None
    log_file: str | None = None
    log_samples: int = 0


@dataclass
class _TaskField:
    extract: Callable[[TaskLogInfo], Any]
    format: Callable[[Any], str]


def _config(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: getattr(info.task.config, n),
        lambda v, n=name: f"{n}={v}",
    )


def _attr(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: getattr(info.task, n),
        lambda v, n=name: f"{n}={v}",
    )


def _arg(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: (
            (info.flow_task.args or {}).get(n) if info.flow_task else None
        ),
        lambda v, n=name: f"{n}={v}",
    )


def _model_role(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: (
            str(info.task.model_roles[n])
            if info.task.model_roles and n in info.task.model_roles
            else None
        ),
        lambda v, n=name: f"{n}={v}",
    )


def _dict_fields(
    dicts: list[Mapping[str, Any] | NotGiven | None],
    make_field: Callable[[str], _TaskField],
) -> list[_TaskField]:
    all_keys: set[str] = set()
    for d in dicts:
        if d:
            all_keys.update(d.keys())
    return [make_field(k) for k in sorted(all_keys)]


def _solver_name(info: TaskLogInfo) -> str | None:
    ri = registry_info(info.task.solver)
    return ri.name if ri else None


def _task_fields(infos: list[TaskLogInfo]) -> list[_TaskField]:
    fields = [
        # Task Args
        *_dict_fields(
            [info.flow_task.args if info.flow_task else None for info in infos], _arg
        ),
        # Model
        _TaskField(lambda info: str(info.task.model) if info.task.model else None, str),
        # Model Roles
        *_dict_fields([info.task.model_roles for info in infos], _model_role),
        # Solver and Approval
        _TaskField(_solver_name, lambda v: f"solver={v}"),
        _TaskField(
            lambda info: str(info.task.approval) if info.task.approval else None,
            lambda v: f"approval={v}",
        ),
        # Task-level fields in task_identifier
        _attr("version"),
        _attr("message_limit"),
        _attr("token_limit"),
        _attr("time_limit"),
        _attr("working_limit"),
        # GenerateConfig fields included in task_identifier
        # (all except max_connections, batch, timeout, attempt_timeout, max_retries)
        _config("temperature"),
        _config("top_p"),
        _config("max_tokens"),
        _config("seed"),
        _config("top_k"),
        _config("num_choices"),
        _config("best_of"),
        _config("frequency_penalty"),
        _config("presence_penalty"),
        _config("stop_seqs"),
        _config("logit_bias"),
        _config("logprobs"),
        _config("top_logprobs"),
        _config("parallel_tool_calls"),
        _config("system_message"),
        _config("cache_prompt"),
        _config("reasoning_effort"),
        _config("reasoning_tokens"),
        _config("effort"),
    ]
    return fields


def _unique_task_names(infos: list[TaskLogInfo]) -> list[tuple[str, str]]:
    names = [info.task.name for info in infos]
    qualifiers: list[list[str]] = [[] for _ in infos]

    for field in _task_fields(infos):
        groups: dict[str, list[int]] = {}
        for i in range(len(infos)):
            key = names[i] + "\0" + ",".join(qualifiers[i])
            groups.setdefault(key, []).append(i)

        for group in groups.values():
            if len(group) < 2:
                continue
            values = [field.extract(infos[i]) for i in group]
            if len(set(str(v) for v in values)) <= 1:
                continue
            for i, val in zip(group, values, strict=True):
                if val is not None:
                    qualifiers[i].append(field.format(val))

    return [
        (name, f"({', '.join(qualifiers[i])})" if qualifiers[i] else "")
        for i, name in enumerate(names)
    ]


def create_task_log_display(task_log_info: dict[str, TaskLogInfo]) -> Table:
    total = len(task_log_info)
    num_complete = sum(
        1
        for info in task_log_info.values()
        if info.task_samples is not None and info.log_samples >= info.task_samples
    )
    if num_complete > 0:
        remaining = total - num_complete
        header = f"Running {quantity(remaining, 'task')} ({quantity(num_complete, 'task')} already complete)"
    else:
        header = f"Running {quantity(total, 'task')}"

    infos = list(task_log_info.values())
    name_quals = _unique_task_names(infos)
    max_name_len = max((len(n) for n, _ in name_quals), default=0)

    table = Table(show_edge=False, box=None, padding=(0, 1))
    table.add_column(header)
    table.add_column("Existing Samples", justify="right")
    table.add_row("", "")
    for info, (base_name, qual) in zip(infos, name_quals, strict=True):
        name = Text(base_name)
        if qual:
            name.append(" " * (max_name_len - len(base_name) + 1))
            name.append(qual)
        if info.log_file:
            name.append(
                f"\n{' ' * (max_name_len + 1)}{path_str(info.log_file)}", style="dim"
            )
        samples = (
            f"{info.log_samples}/{info.task_samples}"
            if info.task_samples is not None
            else ""
        )
        table.add_row(name, samples)
    return table
