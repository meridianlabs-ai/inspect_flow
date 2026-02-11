"""Console display for flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from types import TracebackType
from typing import Any, Literal, Optional, Type, TypedDict

from inspect_flow._util.console import Formats, console, format_prefix, print
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.live import Live
from rich.measure import Measurement
from rich.segment import Segment
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from typing_extensions import Unpack

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


class DisplayActionArgs(TypedDict, total=False):
    status: ActionStatus
    info: RenderableType | list[RenderableType]


@dataclass
class DisplayAction:
    description: str | None = None
    status: ActionStatus | None = None
    info: RenderableType | list[RenderableType] | None = None

    def update(self, action: DisplayAction) -> None:
        for field in fields(DisplayAction):
            val = getattr(action, field.name)
            if val is not None:
                setattr(self, field.name, val)


class RunAction:
    def __init__(self, key: str, **kwargs: Unpack[DisplayActionArgs]) -> None:
        self.key = key
        self.action = DisplayAction(**kwargs)

    def __enter__(self) -> RunAction:
        self.action.status = "running"
        display().update_action(self.key, self.action)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.action.status != "running":
            return

        if exc_val:
            self.action.status = "error"
            self.action.info = str(exc_val)
        else:
            self.action.status = "success"
        display().update_action(self.key, self.action)

    def update(self, **kwargs: Unpack[DisplayActionArgs]) -> None:
        self.action.update(DisplayAction(**kwargs))
        display().update_action(self.key, self.action)

    def print(self, *objects: Any, format: Formats = "default", **kwargs: Any) -> None:
        display().print(*objects, action_key=self.key, format=format, **kwargs)


class _BorderedTable:
    """Table wrapped in a box border. Shows [DRY RUN] in each corner when enabled."""

    def __init__(
        self,
        inner: Table,
        dry_run: bool,
        messages: dict[str, list[Text]] | None = None,
    ) -> None:
        self._inner = inner
        self._dry_run = dry_run
        self._messages = messages or {}

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

        separator = f"├{'─' * (width - 2)}┤\n"
        blank = f"│{' ' * (width - 2)}│\n"
        first_group = True
        for msgs in self._messages.values():
            if not msgs:
                continue
            if first_group:
                yield Segment(separator)
                first_group = False
            else:
                yield Segment(blank)
            for msg in msgs:
                for line in console.render_lines(msg, inner_options, pad=True):
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
    def update_action(self, key: str, action: DisplayAction) -> None: ...

    @abstractmethod
    def print(
        self, *objects: Any, action_key: str, format: Formats = "default", **kwargs: Any
    ) -> None: ...


class SimpleDisplay(Display):
    def __init__(self) -> None:
        self._last_action_key: str | None = None

    def update_action(self, key: str, action: DisplayAction) -> None:
        status = action.status or "pending"
        char, style = _ICON.get(status, _ICON["pending"])
        line = Text()
        line.append(char, style=style)
        line.append(f" {action.description or key}")
        console.print(line, *_info_renderables(action.info))

    def print(
        self, *objects: Any, action_key: str, format: Formats = "default", **kwargs: Any
    ) -> None:
        if self._last_action_key is not None and self._last_action_key != action_key:
            console.print()
        self._last_action_key = action_key
        print(*objects, format=format, **kwargs)


class LiveDisplay(Display):
    def __init__(self, dry_run: bool, actions: dict[str, DisplayAction]) -> None:
        self.dry_run = dry_run
        self._actions: dict[str, DisplayAction] = actions
        self._messages: dict[str, list[Text]] = {}
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

    def update_action(self, key: str, action: DisplayAction) -> None:
        existing = self._actions.get(key)
        if existing:
            existing.update(action)
        else:
            self._actions[key] = action
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
        for key, action in self._actions.items():
            table.add_row(
                self._status_icon(action.status or "pending"),
                Text(action.description or key),
                *_info_renderables(action.info),
            )
        return _BorderedTable(table, self.dry_run, self._messages)

    def print(
        self, *objects: Any, action_key: str, format: Formats = "default", **kwargs: Any
    ) -> None:
        parts: list[str | Text] = []
        prefix = format_prefix(format)
        if prefix:
            parts.extend([prefix, " "])
        for i, obj in enumerate(objects):
            if i > 0:
                parts.append(" ")
            parts.append(obj if isinstance(obj, (str, Text)) else str(obj))
        self._messages.setdefault(action_key, []).append(Text.assemble(*parts))
        if self._live:
            self._live.update(self._make_display())
