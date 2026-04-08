"""Console display for flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Literal, Optional, Type

from rich.console import RenderableType
from rich.text import Text

from inspect_flow._display.action import DisplayAction
from inspect_flow._util.console import Formats

DisplayType = Literal["full", "rich", "plain"]
"""Display type for flow output."""

DisplayMode = Literal["run", "dry_run", "check"]
"""Display mode for flow output.

Options:
    - "full": Full interactive display with progress bars and rich formatting
    - "rich": Rich text formatting without interactive elements
    - "plain": Plain text output
"""
_display_type: DisplayType = "rich"
_display: Display | None = None


def get_display_type() -> DisplayType:
    return _display_type


def set_display_type(display_type: DisplayType) -> None:
    global _display_type
    _display_type = display_type


def display() -> Display:
    global _display
    if _display is None:
        if _display_type == "plain":
            from inspect_flow._display.plain import PlainDisplay

            _display = PlainDisplay()
        else:
            from inspect_flow._display.full import FullDisplay

            _display = FullDisplay()
    return _display


def set_display(d: Display | None) -> None:
    global _display
    _display = d


class Display(ABC):
    @abstractmethod
    def update_action(self, key: str, action: DisplayAction) -> None: ...

    @abstractmethod
    def print(
        self,
        *objects: RenderableType,
        action_key: str,
        format: Formats = "default",
        copyable: bool = False,
    ) -> None: ...

    @abstractmethod
    def set_footer(self, renderable: RenderableType | None) -> None: ...

    @abstractmethod
    def get_title(self) -> list[str | Text] | None: ...

    @abstractmethod
    def set_title(self, *objects: str | Text) -> None: ...

    @abstractmethod
    def __enter__(self) -> Display: ...

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None: ...

    @abstractmethod
    def stop(self, remove_actions: list[str] | None = None) -> None: ...


def create_display(mode: DisplayMode, actions: dict[str, DisplayAction]) -> Display:
    if _display_type == "plain":
        from inspect_flow._display.plain import PlainDisplay

        return PlainDisplay()
    else:
        from inspect_flow._display.full_actions import FullActionsDisplay

        return FullActionsDisplay(mode=mode, actions=actions)
