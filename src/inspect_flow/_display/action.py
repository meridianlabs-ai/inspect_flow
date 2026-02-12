"""Console display for flow."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Literal, TypedDict

from rich.console import RenderableType

ActionStatus = Literal["pending", "running", "success", "error"]

ACTION_ICONS: dict[ActionStatus, tuple[str, str]] = {
    "pending": ("○", "dim"),
    "success": ("✓", "green"),
    "error": ("✗", "red"),
}


def info_renderables(
    info: RenderableType | list[RenderableType] | None,
) -> list[RenderableType]:
    if info is None:
        return []
    if isinstance(info, list):
        return info
    return [info]


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
