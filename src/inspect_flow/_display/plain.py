"""Plain text display with no colors or special characters."""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from rich.console import Console, RenderableType
from rich.text import Text

from inspect_flow._display.action import DisplayAction
from inspect_flow._display.display import Display, set_display
from inspect_flow._util.console import Formats

console = Console(no_color=True, highlight=False)

PLAIN_ICONS: dict[str, str] = {
    "pending": "[ ]",
    "running": "[..]",
    "success": "[OK]",
    "error": "[ERROR]",
}

PLAIN_FORMAT_PREFIX: dict[Formats, str] = {
    "default": "",
    "success": "[OK]",
    "info": "[INFO]",
    "warning": "[WARN]",
    "error": "[ERROR]",
}


class PlainDisplay(Display):
    def __init__(self) -> None:
        self._started = False
        self._last_action_key: str | None = None
        self._title: list[str | Text] | None = None

    def update_action(self, key: str, action: DisplayAction) -> None:
        icon = PLAIN_ICONS.get(action.status or "pending", "[ ]")
        desc = action.description or key
        info_parts: list[RenderableType] = []
        if action.info is not None:
            infos = action.info if isinstance(action.info, list) else [action.info]
            info_parts = list(infos)
        console.print(f"{icon} {desc}", *info_parts)

    def print(
        self, *objects: RenderableType, action_key: str, format: Formats = "default"
    ) -> None:
        if self._last_action_key is not None and self._last_action_key != action_key:
            console.print()
        self._last_action_key = action_key
        prefix = PLAIN_FORMAT_PREFIX.get(format, "")
        if prefix:
            console.print(prefix, *objects)
        else:
            console.print(*objects)

    def set_footer(self, renderable: RenderableType | None) -> None:
        pass

    def get_title(self) -> list[str | Text] | None:
        return self._title

    def set_title(self, *objects: str | Text) -> None:
        self._title = list(objects) if objects else None
        if objects:
            console.print(*objects)

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
        if not self._started:
            return
        set_display(None)
        self._started = False
