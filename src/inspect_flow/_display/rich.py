"""Rich display with Live footer support."""

from __future__ import annotations

from rich.console import RenderableType
from rich.live import Live

from inspect_flow._display.plain import PlainDisplay
from inspect_flow._util.console import console


class RichDisplay(PlainDisplay):
    def __init__(self) -> None:
        super().__init__(actions={})
        self._live: Live | None = None

    def set_footer(self, renderable: RenderableType | None) -> None:
        if renderable is not None:
            if self._live is None:
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

    def stop(self) -> None:
        self._stop_live()
        super().stop()
