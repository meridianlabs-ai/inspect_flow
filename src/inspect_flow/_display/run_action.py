"""Console display for flow."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Optional, Type

from typing_extensions import Unpack

from inspect_flow._display.action import DisplayAction, DisplayActionArgs
from inspect_flow._display.display import display
from inspect_flow._util.console import Formats


class RunAction:
    def __init__(self, key: str, **kwargs: Unpack[DisplayActionArgs]) -> None:
        self.key = key
        self.action = DisplayAction(**kwargs)

    def __enter__(self) -> RunAction:
        self.action.status = "running"
        display().update_action(self.key, self.action)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.action.status != "running":
            return

        if exc_val:
            self.action.status = "error"
            self.action.info = str(exc_val)
        else:
            self.action.status = "success"
        display().update_action(self.key, self.action)

    def update(self, **kwargs: Unpack[DisplayActionArgs]) -> None:
        self.action.update(DisplayAction(**kwargs))
        display().update_action(self.key, self.action)

    def print(self, *objects: Any, format: Formats = "default", **kwargs: Any) -> None:
        display().print(*objects, action_key=self.key, format=format, **kwargs)
