from __future__ import annotations

import inspect
import types
from pathlib import Path
from typing import Any, cast

import click
import griffe
from inspect_ai._util.module import load_module
from inspect_ai._util.registry import registry_find, registry_info

from inspect_flow._steps.step import STEP_TYPE, WrappedStepFunction
from inspect_flow._store.store import store_factory
from inspect_flow._util.path_util import find_auto_includes
from inspect_flow.api import run_step


def _discover_steps() -> list[tuple[str, WrappedStepFunction]]:
    """Load _flow.py files and return all registered @step functions."""
    import inspect_flow._steps  # noqa: F401

    for flow_file in find_auto_includes(str(Path.cwd())):
        load_module(Path(flow_file))
    steps = cast(
        list[WrappedStepFunction], registry_find(lambda info: info.type == STEP_TYPE)
    )
    return [(registry_info(s).name.split("/")[-1], s) for s in steps]


class StepGroup(click.Group):
    """Click group that lazily discovers @step-decorated functions as subcommands."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(name for name, _ in _discover_steps())

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        for name, func in _discover_steps():
            if name == cmd_name:
                return _step_to_command(name, func)
        return None


def _parse_arg_help(doc: str) -> dict[str, str]:
    import logging

    griffe_logger = logging.getLogger("griffe")
    prev_level = griffe_logger.level
    griffe_logger.setLevel(logging.ERROR)
    try:
        parsed = griffe.Docstring(doc, parser="google")
        result: dict[str, str] = {}
        for section in parsed.parsed:
            if isinstance(section, griffe.DocstringSectionParameters):
                for param in section.value:
                    result[param.name] = param.description
    finally:
        griffe_logger.setLevel(prev_level)
    return result


def _step_to_command(name: str, func: WrappedStepFunction) -> click.Command:
    """Convert a @step function into a click.Command."""
    original = getattr(func, "_step_func", func)
    sig = inspect.signature(original)
    params: list[click.Parameter] = []
    doc = inspect.getdoc(original) or ""
    arg_help = _parse_arg_help(doc)

    # Skip the first parameter (logs: list[EvalLog]) — provided via PATH arg
    step_params = list(sig.parameters.values())[1:]
    dict_params: set[str] = set()
    for param in step_params:
        option_name = f"--{param.name.replace('_', '-')}"
        annotation = (
            param.annotation if param.annotation != inspect.Parameter.empty else str
        )
        help_text = arg_help.get(param.name)

        has_default = param.default is not inspect.Parameter.empty
        default = param.default if has_default else None
        required = not has_default

        if annotation is bool:
            params.append(
                click.Option(
                    [option_name],
                    is_flag=True,
                    default=default if has_default else False,
                    help=help_text,
                )
            )
        elif _is_list_of_str(annotation):
            params.append(
                click.Option(
                    [option_name],
                    multiple=True,
                    type=str,
                    default=default or (),
                    required=required,
                    help=help_text,
                )
            )
        elif _is_dict_of_str(annotation):
            dict_params.add(param.name)
            params.append(
                click.Option(
                    [option_name],
                    multiple=True,
                    type=str,
                    default=default or (),
                    required=required,
                    help=help_text,
                )
            )
        else:
            params.append(
                click.Option(
                    [option_name],
                    type=_annotation_to_click_type(annotation),
                    default=default,
                    required=required,
                    help=help_text,
                )
            )

    # Add PATH argument and common options
    params.insert(
        0,
        click.Argument(["path"], nargs=-1, required=False, type=click.Path()),
    )
    params.append(
        click.Option(
            ["--store", "-s"],
            is_flag=False,
            flag_value="auto",
            default=None,
            help="Resolve logs from a store. Use --store for the default store or --store PATH for a specific one.",
        )
    )
    params.append(
        click.Option(
            ["--filter"],
            type=str,
            multiple=True,
            help="Log filter. Only process logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass).",
        )
    )
    params.append(
        click.Option(
            ["--exclude"],
            type=str,
            multiple=True,
            help="Log filter. Exclude logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times.",
        )
    )
    params.append(
        click.Option(
            ["--recursive/--no-recursive"],
            default=True,
            help="Recurse into directories (default: true). No effect when --store is used.",
        )
    )
    params.append(
        click.Option(
            ["--dry-run"],
            is_flag=True,
            default=False,
            help="Preview changes without writing to disk.",
        )
    )

    help_text = doc.split("\n\n")[0] if doc else ""

    def callback(path: tuple[str, ...], **kwargs: Any) -> None:
        for dp in dict_params:
            if dp in kwargs:
                kwargs[dp] = _parse_key_value_pairs(kwargs[dp])
        store = kwargs.pop("store", None)
        if path and store:
            raise click.UsageError("PATH and --store are mutually exclusive.")
        if not path and not store:
            raise click.UsageError("Either PATH or --store is required.")
        if store:
            flow_store = store_factory(str(store), base_dir=".", create=False)
            if not flow_store:
                raise click.UsageError(f"Could not open store at {store}")
            logs: list[str] = list(flow_store.get_logs())
        else:
            logs = list(path)
        run_step(func, logs, **kwargs)

    return click.Command(
        name=name,
        params=params,
        callback=callback,
        help=help_text,
    )


def _annotation_to_click_type(annotation: object) -> type:
    if annotation is str or annotation is inspect.Parameter.empty:
        return str
    if annotation is int:
        return int
    if annotation is float:
        return float
    if annotation is bool:
        return bool
    return str


def _is_dict_of_str(annotation: object) -> bool:
    origin = getattr(annotation, "__origin__", None)
    if origin is dict:
        return True
    if isinstance(annotation, types.UnionType):
        args = getattr(annotation, "__args__", ())
        return any(_is_dict_of_str(a) for a in args)
    return False


def _parse_key_value_pairs(values: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise click.BadParameter(f"Expected key=value format, got: {item}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def _is_list_of_str(annotation: object) -> bool:
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())
    if origin is list and args == (str,):
        return True
    # Handle list[str] | None
    if isinstance(annotation, types.UnionType):
        return any(_is_list_of_str(a) for a in args)
    return False


@click.group("step", cls=StepGroup, help="Run workflow steps on eval logs")
def step_command() -> None:
    pass
