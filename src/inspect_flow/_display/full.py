"""Rich display with styled output and Live footer support."""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from rich.console import RenderableType
from rich.live import Live
from rich.text import Text

from inspect_flow._display.action import ACTION_ICONS, DisplayAction, info_renderables
from inspect_flow._display.display import Display, set_display
from inspect_flow._util.console import Formats, console, flow_print, join


class FullDisplay(Display):
    def __init__(self) -> None:
        self._started = False
        self._last_action_key: str | None = None
        self._title: list[str | Text] | None = None
        self._live: Live | None = None
        self._was_recording = False

    def update_action(self, key: str, action: DisplayAction) -> None:
        status = action.status or "pending"
        char, style = ACTION_ICONS.get(status, ACTION_ICONS["pending"])
        line = Text()
        line.append(char, style=style)
        line.append(f" {action.description or key}")
        console.print(line, *info_renderables(action.info))

    def print(
        self,
        *objects: RenderableType,
        action_key: str,
        format: Formats = "default",
        copyable: bool = False,
    ) -> None:
        if self._last_action_key is not None and self._last_action_key != action_key:
            console.print()
        self._last_action_key = action_key
        flow_print(*objects, format=format)

    def set_footer(self, renderable: RenderableType | None) -> None:
        if renderable is not None:
            if self._live is None:
                self._was_recording = console.record
                console.record = False
                self._live = Live(
                    renderable,
                    console=console,
                    transient=True,
                    refresh_per_second=10,
                )
                self._live.start()
            else:
                self._live.update(renderable)
        else:
            self._stop_live()

    def _stop_live(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None
            console.record = self._was_recording

    def get_title(self) -> list[str | Text] | None:
        return self._title

    def set_title(self, *objects: str | Text) -> None:
        self._title = list(objects) if objects else None
        if objects:
            console.print(join(list(objects)))

    def __enter__(self) -> Display:
        set_display(self)
        self._started = True
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def stop(self, remove_actions: list[str] | None = None) -> None:
        self._stop_live()
        if not self._started:
            return
        set_display(None)
        self._started = False
