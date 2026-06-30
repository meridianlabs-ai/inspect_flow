import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from typing import Any

import click

from inspect_flow._display.display import (
    get_display,
    get_display_type,
    set_display,
    set_display_type,
)
from inspect_flow._util.console import console


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


def emit_json(data: Any) -> None:
    click.echo(json.dumps(data, indent=2, default=str))
