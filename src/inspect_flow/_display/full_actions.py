"""Full actions display with bordered table and live updates."""

from __future__ import annotations

import logging
import os
import sys
import threading
import traceback
from time import sleep
from types import TracebackType
from typing import Any, Optional, Type

from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.live import Live
from rich.measure import Measurement
from rich.segment import Segment
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from inspect_flow._display.action import (
    ACTION_ICONS,
    ActionStatus,
    DisplayAction,
    info_renderables,
)
from inspect_flow._display.display import Display, DisplayMode, set_display
from inspect_flow._util.console import Formats, console, format_prefix, join

logger = logging.getLogger(__name__)


class _SafeRenderable:
    """Wraps a renderable to catch errors, preventing Live's refresh thread from dying silently."""

    def __init__(self, inner: RenderableType) -> None:
        self._inner = inner

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        try:
            yield from console.render(self._inner, options)
        except Exception:
            logger.exception("Display render error")
            try:
                yield from console.render(traceback.format_exc(), options)
            except Exception:
                pass


class _Copyable:
    """Marker for messages that should render without borders when they would wrap."""

    def __init__(self, renderable: RenderableType) -> None:
        self.renderable = renderable

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield from console.render(self.renderable, options)


_MODE_INSET: dict[str, str] = {
    "dry_run": "[DRY RUN]",
    "check": "[CHECK]",
}


class _BorderedTable:
    """Table wrapped in a box border. Shows a mode label in each corner when applicable."""

    def __init__(
        self,
        inner: Table,
        mode: DisplayMode,
        messages: dict[str, list[RenderableType]] | None = None,
        footer: RenderableType | None = None,
        title: list[str | Text] | None = None,
        height: int | None = None,
        console_output: list[str] | None = None,
    ) -> None:
        self._inner = inner
        self._mode = mode
        self._messages = messages or {}
        self._footer = footer
        self._title = title
        self._height = height
        self._console_output = console_output or []

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        inset_text = _MODE_INSET.get(self._mode, "")
        inset = f"─{inset_text}─" if inset_text else ""

        width = options.max_width
        inner_width = width - 4  # "│ " + " │"

        if self._title is not None:
            spaced = [x for p in self._title for x in (" ", p)][1:]
            title_text = Text.assemble(" [", *spaced, "] ")
            title_width = title_text.cell_len
        else:
            title_text = None
            title_width = 0
        fill = max(0, width - 2 - title_width - 2 * len(inset))
        left_fill = fill // 2
        right_fill = fill - left_fill
        yield Segment(f"╭{inset}{'─' * left_fill}")
        if title_text:
            yield from title_text.render(console)
        yield Segment(f"{'─' * right_fill}{inset}╮\n")

        inner_options = options.update_width(inner_width)
        separator = f"├{'─' * (width - 2)}┤\n"
        blank = f"│{' ' * (width - 2)}│\n"

        def bordered(line: list[Segment]) -> list[Segment]:
            return [Segment("│ "), *line, Segment(" │\n")]

        # Pinned: actions table + separator (always visible)
        pinned: list[list[Segment]] = []
        for line in console.render_lines(self._inner, inner_options, pad=True):
            pinned.append(bordered(line))
        pinned.append([Segment(separator)])

        # Scrollable: messages, footer, console output (last N shown)
        scrollable: list[list[Segment]] = []
        first_msg = True
        for msgs in self._messages.values():
            if not msgs:
                continue
            if not first_msg:
                scrollable.append([Segment(blank)])
            first_msg = False
            for msg in msgs:
                if isinstance(msg, _Copyable):
                    if self._height is None:
                        continue  # Final render: printed after the box
                    renderable = msg.renderable
                else:
                    renderable = msg
                for line in console.render_lines(renderable, inner_options, pad=True):
                    scrollable.append(bordered(line))
        if self._footer is not None:
            scrollable.append([Segment(blank)])
            for line in console.render_lines(self._footer, inner_options, pad=True):
                scrollable.append(bordered(line))

        if self._height is not None:
            max_content = self._height - 2  # top + bottom border
            remaining = max_content - len(pinned)
            if self._console_output:
                available = max(remaining - len(scrollable) - 1, 0)
                num_output = min(available, len(self._console_output))
                if num_output > 0:
                    scrollable.append([Segment(blank)])
                    for ol in self._console_output[-num_output:]:
                        text = Text.from_ansi(
                            ol, style="dim", no_wrap=True, overflow="crop"
                        )
                        for line in console.render_lines(text, inner_options, pad=True):
                            scrollable.append(bordered(line))
            for cl in pinned:
                yield from cl
            visible = (
                scrollable[-remaining:] if len(scrollable) > remaining else scrollable
            )
            for cl in visible:
                yield from cl
            for _ in range(remaining - len(visible)):
                yield Segment(blank)
        else:
            for cl in pinned:
                yield from cl
            for cl in scrollable:
                yield from cl

        fill = max(0, width - 2 - 2 * len(inset))
        yield Segment(f"╰{inset}{'─' * fill}{inset}╯\n")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        m = Measurement.get(
            console, options.update_width(options.max_width - 4), self._inner
        )
        return Measurement(m.minimum + 4, m.maximum + 4)


class FullActionsDisplay(Display):
    def __init__(self, mode: DisplayMode, actions: dict[str, DisplayAction]) -> None:
        self._mode: DisplayMode = mode
        self._actions: dict[str, DisplayAction] = actions
        self._messages: dict[str, list[RenderableType]] = {}
        self._footer: RenderableType | None = None
        self._title: list[str | Text] | None = None
        self._live: Live | None = None
        self._output_capture = _OutputCapture()

    def __enter__(self) -> Display:
        assert not self._live
        set_display(self)
        self._output_capture.start()
        self._live = Live(
            self._make_display(),
            console=console,
            transient=True,
            refresh_per_second=10,
        )
        self._live.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._stop(exc_type, exc_val, exc_tb)

    def _stop(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if not self._live:
            return
        if duration := os.environ.get("INSPECT_FLOW_DISPLAY_SLEEP"):  # pragma: no cover
            sleep(float(duration))
        set_display(None)
        self._live.__exit__(exc_type, exc_val, exc_tb)
        self._live = None
        console.print(self._make_display(fill_height=False))
        for msgs in self._messages.values():
            for msg in msgs:
                if isinstance(msg, _Copyable):
                    console.print(msg.renderable, soft_wrap=True, crop=False)
                    (console.file or sys.stdout).write("\n")
        captured = self._output_capture.stop()
        if captured:
            sys.stdout.buffer.write(captured)
            sys.stdout.flush()

    def stop(self, remove_actions: list[str] | None = None) -> None:
        for key in remove_actions or []:
            self._actions.pop(key, None)
        self._stop(None, None, None)

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
        char, style = ACTION_ICONS[status]
        return Text(char, style=style)

    def _make_display(self, fill_height: bool = True) -> _SafeRenderable:
        table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
        table.add_column(width=1)
        table.add_column()
        table.add_column()
        for key, action in self._actions.items():
            table.add_row(
                self._status_icon(action.status or "pending"),
                Text(action.description or key),
                *info_renderables(action.info),
            )
        console_output = (
            self._output_capture.get_recent_lines(console.height)
            if fill_height
            else None
        )
        return _SafeRenderable(
            _BorderedTable(
                table,
                self._mode,
                self._messages,
                self._footer,
                self._title,
                height=console.height - 2 if fill_height else None,
                console_output=console_output,
            )
        )

    def get_title(self) -> list[str | Text] | None:
        return self._title

    def set_title(self, *objects: str | Text) -> None:
        self._title = list(objects) if objects else None
        if self._live:
            self._live.update(self._make_display())

    def set_footer(self, renderable: RenderableType | None) -> None:
        self._footer = renderable
        if self._live:
            self._live.update(self._make_display())

    def print(
        self,
        *objects: RenderableType,
        action_key: str,
        format: Formats = "default",
        copyable: bool = False,
    ) -> None:
        if format != "default":
            prefix = format_prefix(format)
            parts = [prefix, *objects] if prefix else [*objects]
        else:
            parts = list(objects)
        renderable = join(parts)
        if copyable:
            renderable = _Copyable(renderable)
        self._messages.setdefault(action_key, []).append(renderable)
        if self._live:
            self._live.update(self._make_display())


class _OutputCapture:
    """Captures stdout/stderr at the fd level while giving the console direct terminal access."""

    def __init__(self) -> None:
        self._captured = bytearray()
        self._lock = threading.Lock()
        self._saved_fds: dict[int, int] = {}
        self._pipes: dict[int, int] = {}
        self._threads: list[threading.Thread] = []
        self._console_file: Any = None

    def start(self) -> None:
        for fd in (1, 2):
            self._saved_fds[fd] = os.dup(fd)
            pipe_r, pipe_w = os.pipe()
            self._pipes[fd] = pipe_r
            os.dup2(pipe_w, fd)
            os.close(pipe_w)
            thread = threading.Thread(target=self._drain, args=(fd,), daemon=True)
            thread.start()
            self._threads.append(thread)
        # Give the console a direct file to the terminal (bypassing redirected fd 1)
        self._console_file = os.fdopen(os.dup(self._saved_fds[1]), "w")
        console._file = self._console_file

    def _drain(self, fd: int) -> None:
        pipe_r = self._pipes[fd]
        while True:
            try:
                data = os.read(pipe_r, 4096)
                if not data:
                    break
                with self._lock:
                    self._captured.extend(data)
            except OSError:
                break

    def get_recent_lines(self, max_lines: int) -> list[str]:
        with self._lock:
            text = self._captured.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return lines[-max_lines:] if lines else []

    def stop(self) -> bytes:
        for fd, saved in self._saved_fds.items():
            os.dup2(saved, fd)
            os.close(saved)
        # Close pipe read ends to unblock drain threads (os.read returns OSError)
        for pipe_r in self._pipes.values():
            os.close(pipe_r)
        for thread in self._threads:
            thread.join()
        console._file = None
        if self._console_file:
            self._console_file.close()
        return bytes(self._captured)
