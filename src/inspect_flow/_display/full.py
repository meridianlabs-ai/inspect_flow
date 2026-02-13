"""Console display for flow."""

from __future__ import annotations

import os
import threading
from time import sleep
from typing import Any

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
from inspect_flow._display.display import Display, set_display
from inspect_flow._util.console import Formats, console, format_prefix, join


class _BorderedTable:
    """Table wrapped in a box border. Shows [DRY RUN] in each corner when enabled."""

    def __init__(
        self,
        inner: Table,
        dry_run: bool,
        messages: dict[str, list[RenderableType]] | None = None,
        footer: RenderableType | None = None,
        title: str | Text | list[str | Text] | None = None,
        height: int | None = None,
        console_output: list[str] | None = None,
    ) -> None:
        self._inner = inner
        self._dry_run = dry_run
        self._messages = messages or {}
        self._footer = footer
        self._title = title
        self._height = height
        self._console_output = console_output or []

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
        if self._title is not None:
            title_parts = (
                self._title if isinstance(self._title, list) else [self._title]
            )
            spaced = [x for p in title_parts for x in (" ", p)][1:]
            title_text = Text.assemble("[", *spaced, "]")
            title_width = title_text.cell_len
        else:
            title_text = None
            title_width = 0
        fill = max(0, width - len(tl) - len(tr) - title_width - 2 * len(inset) - 2)
        left_fill = fill // 2
        right_fill = fill - left_fill
        yield Segment(f"╭{inset}{tl}{'─' * left_fill}")
        if title_text:
            yield from title_text.render(console)
        yield Segment(f"{'─' * right_fill}{tr}{inset}╮\n")

        inner_options = options.update_width(inner_width)
        lines_yielded = 1  # top border
        for line in console.render_lines(self._inner, inner_options, pad=True):
            yield Segment("│ ")
            yield from line
            yield Segment(" │\n")
            lines_yielded += 1

        separator = f"├{'─' * (width - 2)}┤\n"
        blank = f"│{' ' * (width - 2)}│\n"
        first_group = True
        for msgs in self._messages.values():
            if not msgs:
                continue
            if first_group:
                yield Segment(separator)
                lines_yielded += 1
                first_group = False
            else:
                yield Segment(blank)
                lines_yielded += 1
            for msg in msgs:
                for line in console.render_lines(msg, inner_options, pad=True):
                    yield Segment("│ ")
                    yield from line
                    yield Segment(" │\n")
                    lines_yielded += 1

        if self._footer is not None:
            yield Segment(separator if first_group else blank)
            lines_yielded += 1
            for line in console.render_lines(self._footer, inner_options, pad=True):
                yield Segment("│ ")
                yield from line
                yield Segment(" │\n")
                lines_yielded += 1

        if self._height is not None and self._console_output:
            available = self._height - lines_yielded - 1  # -1 for bottom border
            num_lines = max(min(available, len(self._console_output)), 5)
            output_lines = self._console_output[-num_lines:]
            yield Segment(separator if first_group else blank)
            lines_yielded += 1
            for ol in output_lines:
                text = Text.from_ansi(ol, style="dim", no_wrap=True, overflow="crop")
                for line in console.render_lines(text, inner_options, pad=True):
                    yield Segment("│ ")
                    yield from line
                    yield Segment(" │\n")
                    lines_yielded += 1
            remaining = self._height - lines_yielded - 1
            for _ in range(remaining):
                yield Segment(blank)
        elif self._height is not None:
            padding = self._height - lines_yielded - 1
            for _ in range(padding):
                yield Segment(blank)

        fill = max(0, width - len(bl) - len(br) - 2 * len(inset) - 2)
        yield Segment(f"╰{inset}{bl}{'─' * fill}{br}{inset}╯\n")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        m = Measurement.get(
            console, options.update_width(options.max_width - 4), self._inner
        )
        return Measurement(m.minimum + 4, m.maximum + 4)


class FullDisplay(Display):
    def __init__(self, dry_run: bool, actions: dict[str, DisplayAction]) -> None:
        self.dry_run = dry_run
        self._actions: dict[str, DisplayAction] = actions
        self._messages: dict[str, list[RenderableType]] = {}
        self._footer: RenderableType | None = None
        self._title: str | Text | list[str | Text] | None = None
        self._live: Live | None = None
        self._output_capture = _OutputCapture()

    def __enter__(self) -> Display:
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

    def __exit__(self, *args: Any) -> None:
        sleep(5)
        if self._live:
            self._live.__exit__(*args)
        captured = self._output_capture.stop()
        if captured:
            import sys

            sys.stdout.buffer.write(captured)
            sys.stdout.flush()
        console.print(self._make_display(fill_height=False))
        set_display(None)

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

    def _make_display(self, fill_height: bool = True) -> _BorderedTable:
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
        return _BorderedTable(
            table,
            self.dry_run,
            self._messages,
            self._footer,
            self._title,
            height=console.height - 2 if fill_height else None,
            console_output=console_output,
        )

    def set_title(self, title: str | Text | list[str | Text] | None) -> None:
        self._title = title
        if self._live:
            self._live.update(self._make_display())

    def set_footer(self, renderable: RenderableType | None) -> None:
        self._footer = renderable
        if self._live:
            self._live.update(self._make_display())

    def print(
        self, *objects: Any, action_key: str, format: Formats = "default", **kwargs: Any
    ) -> None:
        prefix = format_prefix(format)
        parts = [prefix, *objects] if prefix else [*objects]
        renderable = join(parts)
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
        for thread in self._threads:
            thread.join()
        for pipe_r in self._pipes.values():
            os.close(pipe_r)
        console._file = None
        if self._console_file:
            self._console_file.close()
        return bytes(self._captured)
