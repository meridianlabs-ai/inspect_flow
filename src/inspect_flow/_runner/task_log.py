from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from inspect_ai import Task
from inspect_ai._util.registry import registry_info
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from inspect_flow._types.flow_types import (
    FlowTask,
    NotGiven,
)
from inspect_flow._util.console import path, pluralize


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
        _TaskField(
            lambda info: getattr(info.task.config, "system_message", None),
            lambda v: "system_message=...",
        ),
        _config("cache_prompt"),
        _config("reasoning_effort"),
        _config("reasoning_tokens"),
        _config("effort"),
    ]
    return fields


def _unique_task_names(infos: list[TaskLogInfo]) -> list[tuple[str, Text]]:
    names = [info.task.name for info in infos]
    qualifiers: list[list[str]] = [[] for _ in infos]

    for i, info in enumerate(infos):
        if info.task.model:
            qualifiers[i].append(str(info.task.model))

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

    result: list[tuple[str, Text]] = []
    for i, name in enumerate(names):
        if qualifiers[i]:
            qual = Text("(", style="dim")
            for j, q in enumerate(qualifiers[i]):
                if j > 0:
                    qual.append(", ", style="dim")
                key, sep, val = q.partition("=")
                if val:
                    qual.append(key + sep, style="dim")
                    qual.append(val, style="cyan")
                else:
                    qual.append(key, style="cyan")
            qual.append(")", style="dim")
            result.append((name, qual))
        else:
            result.append((name, Text("")))
    return result


def create_task_log_display(
    task_log_info: dict[str, TaskLogInfo],
) -> RenderableType:
    total = len(task_log_info)
    num_complete = sum(
        1
        for info in task_log_info.values()
        if info.task_samples is not None and info.log_samples >= info.task_samples
    )
    NUM = "bold cyan"
    if num_complete > 0:
        remaining = total - num_complete
        header = Text.assemble(
            "Running ",
            (str(remaining), NUM),
            f" {pluralize('task', remaining)} (",
            (str(num_complete), NUM),
            f" {pluralize('task', num_complete)} complete)",
            style="bold",
        )
    else:
        header = Text.assemble(
            "Running ", (str(total), NUM), f" {pluralize('task', total)}", style="bold"
        )

    infos = list(task_log_info.values())
    name_quals = _unique_task_names(infos)

    have_logs = any(info.log_file for info in infos)

    table = Table(show_edge=False, box=None, padding=(0, 1), expand=False)
    table.add_column("Task", overflow="ellipsis", justify="left")
    table.add_column("")
    if have_logs:
        table.add_column(
            "Existing Log File", no_wrap=True, ratio=2, overflow="ellipsis"
        )
    table.add_column("Existing\nSamples", justify="right")
    if not have_logs:
        table.add_row("", "", "")
    else:
        table.add_row("", "", "", "")
    for info, (base_name, qual) in zip(infos, name_quals, strict=True):
        name = Text(base_name)
        samples = (
            f"{info.log_samples}/{info.task_samples}"
            if info.task_samples is not None
            else ""
        )
        if have_logs:
            table.add_row(
                name, qual, path(info.log_file) if info.log_file else "", samples
            )
        else:
            table.add_row(name, qual, samples)
    return Group(header, table)
