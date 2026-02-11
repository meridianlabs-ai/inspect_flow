"""Console display for flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Any, Literal

from inspect_flow._util.console import console
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.live import Live
from rich.measure import Measurement
from rich.segment import Segment
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

ActionStatus = Literal["pending", "running", "success", "error"]

_ICON: dict[ActionStatus, tuple[str, str]] = {
    "pending": ("○", "dim"),
    "success": ("✓", "green"),
    "error": ("✗", "red"),
}


def _info_renderables(
    info: RenderableType | list[RenderableType] | None,
) -> list[RenderableType]:
    if info is None:
        return []
    if isinstance(info, list):
        return info
    return [info]


_display: Display | None = None


def display() -> Display:
    global _display
    if _display is None:
        _display = SimpleDisplay()
    return _display


@dataclass
class DisplayAction:
    key: str
    description: str | None = None
    status: ActionStatus | None = None
    info: RenderableType | list[RenderableType] | None = None


class _BorderedTable:
    """Table wrapped in a box border. Shows [DRY RUN] in each corner when enabled."""

    def __init__(self, inner: Table, dry_run: bool) -> None:
        self._inner = inner
        self._dry_run = dry_run

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self._dry_run:
            tl = tr = bl = br = "[DRY RUN]"
        else:
            tl, tr, bl, br = "╭", "╮", "╰", "╯"

        width = options.max_width
        inner_width = width - 4  # "│ " + " │"

        inset = "─" if self._dry_run else ""
        fill = max(0, width - len(tl) - len(tr) - 2 * len(inset) - 2)
        yield Segment(f"╭{inset}{tl}{'─' * fill}{tr}{inset}╮\n")

        inner_options = options.update_width(inner_width)
        for line in console.render_lines(self._inner, inner_options, pad=True):
            yield Segment("│ ")
            yield from line
            yield Segment(" │\n")

        fill = max(0, width - len(bl) - len(br) - 2 * len(inset) - 2)
        yield Segment(f"╰{inset}{bl}{'─' * fill}{br}{inset}╯\n")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        m = Measurement.get(
            console, options.update_width(options.max_width - 4), self._inner
        )
        return Measurement(m.minimum + 4, m.maximum + 4)


class Display(ABC):
    @abstractmethod
    def update_action(self, action: DisplayAction) -> None: ...


class SimpleDisplay(Display):
    def update_action(self, action: DisplayAction) -> None:
        status = action.status or "pending"
        char, style = _ICON.get(status, _ICON["pending"])
        line = Text()
        line.append(char, style=style)
        line.append(f" {action.description or action.key}")
        console.print(line, *_info_renderables(action.info))


class LiveDisplay(Display):
    def __init__(self, dry_run: bool, actions: list[DisplayAction]) -> None:
        self.dry_run = dry_run
        self._actions: dict[str, DisplayAction] = {a.key: a for a in actions}
        self._live: Live | None = None

    def __enter__(self) -> Display:
        global _display
        _display = self
        self._live = Live(
            self._make_display(),
            console=console,
            transient=False,
            refresh_per_second=10,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._live:
            self._live.__exit__(*args)
        global _display
        _display = None

    def update_action(self, action: DisplayAction) -> None:
        existing = self._actions.get(action.key)
        if existing:
            for field in fields(DisplayAction):
                val = getattr(action, field.name)
                if val is not None:
                    setattr(existing, field.name, val)
        else:
            self._actions[action.key] = action
        if self._live:
            self._live.update(self._make_display())

    def _status_icon(self, status: ActionStatus) -> Text | Spinner:
        if status == "running":
            return Spinner("dots", style="blue")
        char, style = _ICON[status]
        return Text(char, style=style)

    def _make_display(self) -> _BorderedTable:
        table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
        table.add_column(width=1)
        table.add_column()
        table.add_column()
        for action in self._actions.values():
            table.add_row(
                self._status_icon(action.status or "pending"),
                Text(action.description or action.key),
                *_info_renderables(action.info),
            )
        return _BorderedTable(table, self.dry_run)
