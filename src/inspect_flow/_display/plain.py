"""Console display for flow."""

from __future__ import annotations

from typing import Any

from rich.console import RenderableType
from rich.text import Text

from inspect_flow._display.action import ACTION_ICONS, DisplayAction, info_renderables
from inspect_flow._display.display import Display, set_display
from inspect_flow._util.console import Formats, console, flow_print, join


class PlainDisplay(Display):
    def __init__(self, actions: dict[str, DisplayAction]) -> None:
        self._last_action_key: str | None = None
        self._actions = actions

    def update_action(self, key: str, action: DisplayAction) -> None:
        existing = self._actions.get(key)
        if existing:
            existing.update(action)
            action = existing
        else:
            self._actions[key] = action
        status = action.status or "pending"
        char, style = ACTION_ICONS.get(status, ACTION_ICONS["pending"])
        line = Text()
        line.append(char, style=style)
        line.append(f" {action.description or key}")
        console.print(line, *info_renderables(action.info))

    def print(
        self, *objects: Any, action_key: str, format: Formats = "default", **kwargs: Any
    ) -> None:
        if self._last_action_key is not None and self._last_action_key != action_key:
            console.print()
        self._last_action_key = action_key
        flow_print(*objects, format=format, **kwargs)

    def set_footer(self, renderable: RenderableType | None) -> None:
        pass

    def set_title(self, title: RenderableType | list[RenderableType] | None) -> None:
        if title:
            console.print(join(title))

    def __enter__(self) -> Display:
        set_display(self)
        return self

    def __exit__(self, *args: Any) -> None:
        set_display(None)
