from typing import Any, Literal

from inspect_ai._util.file import FileInfo
from inspect_ai.log._file import log_file_info
from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
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


def print(*objects: Any, format: Formats = "default", **kwargs: Any) -> None:
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


class PathProgressDisplay:
    """Progress display that shows recent paths being processed."""

    def __init__(self, description: str, total: int) -> None:
        self._recent_paths: list[str] = []
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
            console=console,
        )
        self._task = self._progress.add_task(description, total=total)
        self._live: Live | None = None

    def __enter__(self) -> "PathProgressDisplay":
        self._live = Live(
            self._make_display(),
            console=console,
            transient=True,
            refresh_per_second=10,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._live:
            self._live.__exit__(*args)

    def _make_display(self) -> Group:
        if self._recent_paths:
            path_lines = [f"  {path_str(p)}" for p in self._recent_paths[-5:]]
            return Group(self._progress, Text("\n".join(path_lines), style="dim"))
        return Group(self._progress)

    def advance(self, path: str) -> None:
        self._recent_paths.append(path)
        self._progress.advance(self._task)
        if self._live:
            self._live.update(self._make_display())
