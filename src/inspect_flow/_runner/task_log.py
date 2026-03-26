from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from inspect_ai import Task
from inspect_ai._util.registry import registry_info
from inspect_ai.model._generate_config import GenerateConfig
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from inspect_flow._types.flow_types import (
    FlowTask,
)
from inspect_flow._util.console import path, pluralize

TaskLogDisplayMode = Literal["check", "pre-run", "post-run"]


@dataclass
class TaskLogInfo:
    task: Task
    flow_task: FlowTask | None = None
    task_samples: int | None = None
    log_file: str | None = None
    log_samples: int = 0


@dataclass
class TaskInfo:
    """Abstract task info for qualifier computation.

    Can be constructed from either a TaskLogInfo (runner) or an EvalLog header (CLI).
    """

    name: str
    model: str | None = None
    args: dict[str, Any] | None = None
    model_roles: dict[str, str] | None = None
    solver: str | None = None
    approval: str | None = None
    version: int | str = 0
    message_limit: int | None = None
    token_limit: int | None = None
    time_limit: int | None = None
    working_limit: int | None = None
    config: GenerateConfig = field(default_factory=GenerateConfig)


def task_log_to_task_info(info: TaskLogInfo) -> TaskInfo:
    task = info.task
    solver_ri = registry_info(task.solver)
    flow_args = info.flow_task.args if info.flow_task else None
    return TaskInfo(
        name=task.name,
        model=str(task.model) if task.model else None,
        args=dict(flow_args) if isinstance(flow_args, dict) else None,
        model_roles=(
            {k: str(v) for k, v in task.model_roles.items()}
            if task.model_roles
            else None
        ),
        solver=solver_ri.name if solver_ri else None,
        approval=str(task.approval) if task.approval else None,
        version=task.version,
        message_limit=task.message_limit,
        token_limit=task.token_limit,
        time_limit=task.time_limit,
        working_limit=task.working_limit,
        config=task.config,
    )


@dataclass
class _TaskField:
    extract: Callable[[TaskInfo], Any]
    format: Callable[[Any], str]


def _config(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: getattr(info.config, n, None),
        lambda v, n=name: f"{n}={v}",
    )


def _simple_attr(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: getattr(info, n, None),
        lambda v, n=name: f"{n}={v}",
    )


def _arg(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: (info.args or {}).get(n),
        lambda v, n=name: f"{n}={v}",
    )


def _model_role(name: str) -> _TaskField:
    return _TaskField(
        lambda info, n=name: (
            info.model_roles[n] if info.model_roles and n in info.model_roles else None
        ),
        lambda v, n=name: f"{n}={v}",
    )


def _dict_fields(
    dicts: list[Mapping[str, Any] | None],
    make_field: Callable[[str], _TaskField],
) -> list[_TaskField]:
    all_keys: set[str] = set()
    for d in dicts:
        if d:
            all_keys.update(d.keys())
    return [make_field(k) for k in sorted(all_keys)]


def _task_fields(infos: list[TaskInfo]) -> list[_TaskField]:
    return [
        # Task Args
        *_dict_fields([info.args for info in infos], _arg),
        # Model Roles
        *_dict_fields([info.model_roles for info in infos], _model_role),
        # Solver and Approval
        _simple_attr("solver"),
        _simple_attr("approval"),
        # Task-level fields in task_identifier
        _simple_attr("version"),
        _simple_attr("message_limit"),
        _simple_attr("token_limit"),
        _simple_attr("time_limit"),
        _simple_attr("working_limit"),
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
            lambda info: getattr(info.config, "system_message", None),
            lambda v: "system_message=...",
        ),
        _config("cache_prompt"),
        _config("reasoning_effort"),
        _config("reasoning_tokens"),
        _config("effort"),
    ]


@dataclass
class _TaskQualifiers:
    names: list[tuple[str, Text]]
    model_only: bool


def unique_task_names(infos: list[TaskInfo]) -> _TaskQualifiers:
    names = [info.name for info in infos]
    qualifiers: list[list[str]] = [[] for _ in infos]

    for i, info in enumerate(infos):
        if info.model:
            qualifiers[i].append(info.model)

    model_only = True
    for task_field in _task_fields(infos):
        groups: dict[str, list[int]] = {}
        for i in range(len(infos)):
            key = names[i] + "\0" + ",".join(qualifiers[i])
            groups.setdefault(key, []).append(i)

        for group in groups.values():
            if len(group) < 2:
                continue
            values = [task_field.extract(infos[i]) for i in group]
            if len({str(v) for v in values}) <= 1:
                continue
            model_only = False
            for i, val in zip(group, values, strict=True):
                if val is not None:
                    qualifiers[i].append(task_field.format(val))

    result: list[tuple[str, Text]] = []
    for i, name in enumerate(names):
        if qualifiers[i]:
            qual = Text()
            for j, q in enumerate(qualifiers[i]):
                if j > 0:
                    qual.append(", ", style="dim")
                key, sep, val = q.partition("=")
                if val:
                    qual.append(key + sep, style="dim")
                    qual.append(val, style="cyan")
                else:
                    qual.append(key, style="cyan")
            result.append((name, qual))
        else:
            result.append((name, Text("")))
    return _TaskQualifiers(
        names=result,
        model_only=model_only,
    )


def _header(task_log_info: dict[str, TaskLogInfo], mode: TaskLogDisplayMode) -> Text:
    total = len(task_log_info)
    num_complete = sum(
        1
        for info in task_log_info.values()
        if info.task_samples is not None and info.log_samples >= info.task_samples
    )

    NUM = "bold cyan"
    if mode == "check":
        missing = total - num_complete
        if missing > 0:
            return Text.assemble(
                "Check: ",
                (str(num_complete), NUM),
                "/",
                (str(total), NUM),
                f" {pluralize('task', total)} complete (",
                (str(missing), NUM),
                f" {pluralize('log', missing)} incomplete)",
                style="bold",
            )
        else:
            return Text.assemble(
                "Check: ",
                (str(total), NUM),
                "/",
                (str(total), NUM),
                f" {pluralize('task', total)} complete",
                style="bold",
            )
    elif mode == "pre-run":
        if num_complete > 0:
            remaining = total - num_complete
            return Text.assemble(
                "Running ",
                (str(remaining), NUM),
                f" {pluralize('task', remaining)} (",
                (str(num_complete), NUM),
                f" {pluralize('task', num_complete)} complete)",
                style="bold",
            )
        else:
            return Text.assemble(
                "Running ",
                (str(total), NUM),
                f" {pluralize('task', total)}",
                style="bold",
            )
    else:  # post-run
        if num_complete < total:
            return Text.assemble(
                "Completed ",
                (str(num_complete), NUM),
                f" of {total} {pluralize('task', total)}",
                style="bold",
            )
        else:
            return Text.assemble(
                "Completed ",
                (str(total), NUM),
                f" {pluralize('task', total)}",
                style="bold",
            )


def create_task_log_display(
    task_log_info: dict[str, TaskLogInfo],
    mode: TaskLogDisplayMode = "pre-run",
) -> RenderableType:
    header = _header(task_log_info, mode)

    infos = list(task_log_info.values())
    qualifiers = unique_task_names([task_log_to_task_info(i) for i in infos])

    have_quals = any(qual for _, qual in qualifiers.names)
    have_logs = any(info.log_file for info in infos)

    adj = "Completed" if mode == "post-run" else "Existing"
    table = Table(show_edge=False, box=None, padding=(0, 1), expand=False)
    table.add_column("Task", overflow="ellipsis", justify="left")
    if have_quals:
        qual_header = "Model" if qualifiers.model_only else "Differentiator"
        table.add_column(qual_header)
    if have_logs:
        table.add_column(f"{adj} Log File", no_wrap=True, ratio=2, overflow="ellipsis")
    table.add_column(f"{adj}\nSamples", justify="right")
    # blank separator row
    table.add_row(*[""] * len(table.columns))
    for info, (base_name, qual) in zip(infos, qualifiers.names, strict=True):
        name = Text(base_name)
        samples = (
            f"{info.log_samples}/{info.task_samples}"
            if info.task_samples is not None
            else ""
        )
        row: list[RenderableType] = [name]
        if have_quals:
            row.append(qual)
        if have_logs:
            row.append(path(info.log_file) if info.log_file else "")
        row.append(samples)
        table.add_row(*row)
    return Group(header, table)
