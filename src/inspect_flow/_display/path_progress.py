from typing import Any

from inspect_ai.log._file import ReadEvalLogsProgress
from rich.console import Group, RenderableType
from rich.progress import BarColumn, Progress, TextColumn
from rich.text import Text

from inspect_flow._display.display import display
from inspect_flow._display.run_action import RunAction
from inspect_flow._util.path_util import path_str


class ReadLogsProgress(ReadEvalLogsProgress):
    """ReadEvalLogsProgress that displays a PathProgressDisplay."""

    def __init__(self, action: RunAction | None = None) -> None:
        self._action = action
        self._display: PathProgressDisplay | None = None

    def __enter__(self) -> "ReadLogsProgress":
        return self

    def __exit__(self, *args: Any) -> None:
        if self._display:
            self._display.__exit__(*args)
            self._display = None

    def before_reading_logs(self, total_files: int) -> None:
        self._display = PathProgressDisplay("Reading logs", total_files, self._action)
        self._display.__enter__()

    def after_read_log(self, log_file: str) -> None:
        if self._display:
            self._display.advance(log_file)


class PathProgressDisplay:
    """Progress display that shows recent paths being processed."""

    def __init__(
        self, description: str, total: int, action: RunAction | None = None
    ) -> None:
        self._has_action = action is not None
        self._recent_paths: list[str] = []
        self._progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
        )
        self._task = self._progress.add_task(description, total=total)
        if action:
            action.update(info=self._progress)
        else:
            display().set_footer(self._progress)

    def __enter__(self) -> "PathProgressDisplay":
        return self

    def __exit__(self, *args: Any) -> None:
        display().set_footer(None)

    def _paths_footer(self) -> Text:
        return Text(
            "\n".join(f"  {path_str(p)}" for p in self._recent_paths[-5:]),
            style="dim",
        )

    def advance(self, path: str) -> None:
        self._recent_paths.append(path)
        self._progress.advance(self._task)
        footer: RenderableType = self._paths_footer()
        if not self._has_action:
            footer = Group(self._progress, footer)
        display().set_footer(footer)
