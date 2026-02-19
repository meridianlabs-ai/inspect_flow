from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from inspect_ai._util.file import FileInfo
from inspect_ai.log._file import log_file_info
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.segment import Segment
from rich.text import Text

from inspect_flow._util.path_util import path_str

console = Console()

Formats = Literal["default", "success", "info", "warning", "error"]


def format_prefix(format: Formats) -> Text:
    if format == "default":
        return Text("")
    elif format == "success":
        return Text("✓", style="green")
    elif format == "info":
        return Text("ℹ", style="blue")
    elif format == "warning":
        return Text("⚠", style="yellow")
    elif format == "error":
        return Text("✗", style="red")


def flow_print(*objects: Any, format: Formats = "default", **kwargs: Any) -> None:
    prefix = format_prefix(format)
    if (
        prefix
        and objects
        and isinstance(objects[0], str)
        and objects[0].startswith("\n")
    ):
        stripped = objects[0].lstrip("\n")
        leading = objects[0][: len(objects[0]) - len(stripped)]
        console.print(leading, end="")
        objects = (prefix, stripped, *objects[1:])
    elif prefix:
        objects = (prefix, *objects)
    console.print(*objects, **kwargs)


def path(p: str) -> Text:
    """Wrap a path for Rich highlighting.

    For log paths, highlights the task name in bright magenta.
    """
    display_path = path_str(p)

    # Try to parse as a log file to extract task name (only for .eval or .json files)
    if p.endswith(".eval") or p.endswith(".json"):
        info = log_file_info(FileInfo(name=p, type="file", size=0, mtime=0))
    else:
        info = None
    if info and info.task:
        # Find the task name in the display path and highlight it
        task_start = display_path.find(f"_{info.task}_")
        if task_start != -1:
            task_start += 1  # Skip the leading underscore
            task_end = task_start + len(info.task)
            text = Text()
            text.append(display_path[:task_start], style="magenta")
            text.append(display_path[task_start:task_end], style="#ffaaff")
            text.append(display_path[task_end:], style="magenta")
            return text

    return Text(display_path, style="magenta")


def pluralize(word: str, count: int, plural: str | None = None) -> str:
    if count == 1:
        return word
    else:
        return plural or (word + "s")


def quantity(count: int, units: str, plural: str | None = None) -> str:
    return f"{count} {pluralize(word=units, count=count, plural=plural)}"


def join(renderables: RenderableType | Sequence[RenderableType]) -> RenderableType:
    if isinstance(renderables, str):
        return renderables
    if isinstance(renderables, Sequence):
        return _Joined(*renderables)
    return renderables


class _Joined:
    def __init__(self, *parts: RenderableType) -> None:
        self._parts = parts

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for i, part in enumerate(self._parts):
            if i > 0:
                yield Segment(" ")
            segments = list(console.render(part, options))
            if segments and segments[-1].text == "\n":
                segments.pop()
            yield from segments
