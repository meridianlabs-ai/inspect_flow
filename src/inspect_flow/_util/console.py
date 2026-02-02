from typing import Any, Literal

from rich.console import Console

from inspect_flow._util.path_util import path_str

console = Console()

Formats = Literal["default", "success", "info", "warning", "error"]


def format_prefix(format: Formats) -> str:
    if format == "default":
        return ""
    elif format == "success":
        return "[green]✓[/green]"
    elif format == "info":
        return "[blue]ℹ[/blue]"
    elif format == "warning":
        return "[yellow]⚠[/yellow]"
    elif format == "error":
        return "[red]✗[/red]"


def print(*objects: Any, format: Formats = "default", **kwargs: Any) -> None:
    prefix = format_prefix(format)
    if (
        prefix
        and objects
        and isinstance(objects[0], str)
        and objects[0].startswith("\n")
    ):
        stripped = objects[0].lstrip("\n")
        leading = objects[0][: len(objects[0]) - len(stripped)]
        console.print(leading, end="")
        objects = (prefix, stripped, *objects[1:])
    elif prefix:
        objects = (prefix, *objects)
    console.print(*objects, **kwargs)


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
