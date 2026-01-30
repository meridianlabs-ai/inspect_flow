from typing import Literal

from rich.console import Console

from inspect_flow._util.path_util import path_str

console = Console()

Formats = Literal["default", "success", "info"]


def _apply_format(msg: str, format: Formats) -> str:
    if format == "success":
        return f"[green]✔[/green] {msg}"
    elif format == "info":
        return f"[blue]ℹ[/blue] {msg}"
    elif format == "default":
        return msg


def print(msg: str, format: Formats = "default") -> None:
    msg = _apply_format(msg, format)
    console.print(msg)


def path(p: str) -> str:
    """Wrap a path for Rich highlighting."""
    return f"[repr.path]{path_str(p)}[/repr.path]"


def pluralize(word: str, count: int, plural: str | None = None) -> str:
    if count == 1:
        return word
    else:
        return plural or (word + "s")


def quantity(count: int, units: str, plural: str | None = None) -> str:
    return f"{count} {pluralize(word=units, count=count, plural=plural)}"
