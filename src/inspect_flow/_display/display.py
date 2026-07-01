"""Console display for flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Literal, Optional, Type

from rich.console import RenderableType
from rich.highlighter import NullHighlighter, ReprHighlighter
from rich.text import Text

from inspect_flow._display.action import DisplayAction
from inspect_flow._util.console import Formats, console

DisplayType = Literal["full", "conversation", "rich", "plain", "log", "none"]
"""Display type for flow output.

Matches Inspect's set of display types:
    - "full": Full interactive display with progress bars and rich formatting.
    - "conversation": Stream the model conversation to the terminal.
    - "rich": Rich text formatting without interactive elements.
    - "plain": Plain text output.
    - "log": Flat, ANSI-free log lines.
    - "none": No display output.
"""

DEFAULT_DISPLAY_TYPE: DisplayType = "full"
"""Default display type for flow output."""

DisplayMode = Literal["run", "dry_run", "check"]
"""Display mode for flow output."""

_PLAIN_DISPLAY_TYPES: tuple[DisplayType, ...] = ("plain", "log")
"""Display types that Flow renders as flat, non-interactive plain text."""

_display_type: DisplayType = DEFAULT_DISPLAY_TYPE
_display: Display | None = None


def get_display_type() -> DisplayType:
    return _display_type


def set_display_type(display_type: DisplayType) -> None:
    global _display_type
    _display_type = display_type
    plain = display_type in _PLAIN_DISPLAY_TYPES or display_type == "none"
    console.no_color = plain
    console.highlighter = NullHighlighter() if plain else ReprHighlighter()
    if display_type == "none":
        # Fully suppress Flow's own console output (flow_print, the result
        # summary). We only ever enable quiet here: JSON commands drive
        # console.quiet themselves via quiet_output(), and clearing it for
        # non-"none" types would clobber that transient suppression when an
        # inner init_output() re-runs mid-command.
        console.quiet = True


def display() -> Display:
    global _display
    if _display is None:
        if _display_type == "none":
            from inspect_flow._display.no import NoDisplay

            _display = NoDisplay()
        elif _display_type in _PLAIN_DISPLAY_TYPES:
            from inspect_flow._display.plain import PlainDisplay

            _display = PlainDisplay()
        else:
            from inspect_flow._display.full import FullDisplay

            _display = FullDisplay()
    return _display


def get_display() -> Display | None:
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

    def make_renderable(self) -> RenderableType | None:
        """Render the current display state, for handoff to another display."""
        return None


def create_display(mode: DisplayMode, actions: dict[str, DisplayAction]) -> Display:
    if _display_type == "none":
        from inspect_flow._display.no import NoDisplay

        return NoDisplay()
    elif _display_type in _PLAIN_DISPLAY_TYPES:
        from inspect_flow._display.plain import PlainDisplay

        return PlainDisplay()
    else:
        from inspect_flow._display.full_actions import FullActionsDisplay

        return FullActionsDisplay(mode=mode, actions=actions)
