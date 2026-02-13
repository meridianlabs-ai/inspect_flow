from typing import Any

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.text import Text

from inspect_flow._display.display import display
from inspect_flow._display.run_action import RunAction
from inspect_flow._util.path_util import path_str


class PathProgressDisplay:
    """Progress display that shows recent paths being processed."""

    def __init__(
        self, description: str, total: int, action: RunAction | None = None
    ) -> None:
        self._recent_paths: list[str] = []
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
        )
        self._task = self._progress.add_task(description, total=total)
        if action:
            action.update(info=self._progress)

    def __enter__(self) -> "PathProgressDisplay":
        return self

    def __exit__(self, *args: Any) -> None:
        display().set_footer(None)

    def _make_footer(self) -> Text:
        path_lines = [f"  {path_str(p)}" for p in self._recent_paths[-5:]]
        return Text("\n".join(path_lines), style="dim")

    def advance(self, path: str) -> None:
        self._recent_paths.append(path)
        self._progress.advance(self._task)
        display().set_footer(self._make_footer())
