"""Silent display that suppresses all output."""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from rich.console import RenderableType
from rich.text import Text

from inspect_flow._display.action import DisplayAction
from inspect_flow._display.display import Display, set_display
from inspect_flow._util.console import Formats


class NoDisplay(Display):
    def __init__(self) -> None:
        self._started = False

    def update_action(self, key: str, action: DisplayAction) -> None:
        pass

    def print(
        self,
        *objects: RenderableType,
        action_key: str,
        format: Formats = "default",
        copyable: bool = False,
    ) -> None:
        pass

    def set_footer(self, renderable: RenderableType | None) -> None:
        pass

    def get_title(self) -> list[str | Text] | None:
        return None

    def set_title(self, *objects: str | Text) -> None:
        pass

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
