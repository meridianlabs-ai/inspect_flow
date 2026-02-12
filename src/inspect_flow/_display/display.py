"""Console display for flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from rich.console import RenderableType

from inspect_flow._display.action import DisplayAction
from inspect_flow._util.console import Formats

DisplayType = Literal["full", "plain"]
_display_type: DisplayType
_display: Display | None = None


def set_display_type(display_type: DisplayType) -> None:
    global _display_type
    _display_type = display_type


def display() -> Display:
    global _display
    if _display is None:
        from inspect_flow._display.plain import PlainDisplay

        _display = PlainDisplay()
    return _display


def set_display(d: Display | None) -> None:
    global _display
    _display = d


class Display(ABC):
    @abstractmethod
    def update_action(self, key: str, action: DisplayAction) -> None: ...

    @abstractmethod
    def print(
        self, *objects: Any, action_key: str, format: Formats = "default", **kwargs: Any
    ) -> None: ...

    @abstractmethod
    def set_footer(self, renderable: RenderableType | None) -> None: ...

    @abstractmethod
    def set_title(
        self, title: RenderableType | list[RenderableType] | None
    ) -> None: ...

    @abstractmethod
    def __enter__(self) -> Display: ...

    @abstractmethod
    def __exit__(self, *args: Any) -> None: ...


def create_display(dry_run: bool, actions: dict[str, DisplayAction]) -> Display:
    if _display_type == "full":
        from inspect_flow._display.full import FullDisplay

        return FullDisplay(dry_run=dry_run, actions=actions)
    else:
        from inspect_flow._display.plain import PlainDisplay

        return PlainDisplay()
