import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from typing import Any

import click

from inspect_flow._display.display import (
    DisplayAction,
    DisplayMode,
    create_display,
    get_display,
    get_display_type,
    set_display,
    set_display_type,
)
from inspect_flow._util.console import console, path


@contextmanager
def quiet_output() -> Iterator[None]:
    prev_display_type = get_display_type()
    prev_display = get_display()
    prev_quiet = console.quiet
    set_display_type("plain")
    console.quiet = True
    try:
        with redirect_stdout(sys.stderr):
            yield
    finally:
        console.quiet = prev_quiet
        set_display_type(prev_display_type)
        set_display(prev_display)


@contextmanager
def output_context(
    output_json: bool,
    *,
    mode: DisplayMode | None = None,
    actions: dict[str, DisplayAction] | None = None,
    config_file: str | None = None,
) -> Iterator[None]:
    """Select the output context for a command based on ``--json``.

    Suppresses display for JSON output; otherwise shows the interactive display
    for ``mode`` (when given) or leaves output untouched.

    Args:
        output_json: Whether the command is emitting JSON.
        mode: Display mode for the interactive (non-JSON) display.
        actions: Display actions for the interactive display.
        config_file: Spec path shown in the interactive display title.
    """
    if output_json:
        with quiet_output():
            yield
    elif mode is not None:
        with create_display(mode=mode, actions=actions or {}) as display:
            if config_file is not None:
                display.set_title("Flow Spec:", path(config_file))
            yield
    else:
        yield


def emit_json(data: Any) -> None:
    click.echo(json.dumps(data, indent=2, default=str))
