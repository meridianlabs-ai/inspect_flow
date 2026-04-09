from collections.abc import Callable
from typing import Any, TypeVar

import click
from inspect_ai._cli.util import parse_cli_args
from inspect_ai._util.constants import (
    ALL_LOG_LEVELS,
)
from inspect_ai._util.file import absolute_file_path
from typing_extensions import TypedDict, Unpack

from inspect_flow._config.load import ConfigOptions
from inspect_flow._display.display import DisplayType, set_display_type
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging

F = TypeVar("F", bound=Callable[..., Any])


_STORE_OPTION_KWARGS: dict[str, Any] = dict(
    is_flag=False,
    flag_value="auto",
    default=None,
    envvar="INSPECT_FLOW_STORE",
)


def store_click_option(help: str = "Path to the store directory.") -> click.Option:
    """Create a ``--store``/``-s`` `click.Option`."""
    return click.Option(["--store", "-s"], help=help, **_STORE_OPTION_KWARGS)


def store_option(f: F, help: str = "Path to the store directory.") -> F:
    """Decorator that adds a ``--store``/``-s`` option."""
    return click.option("--store", "-s", help=help, **_STORE_OPTION_KWARGS)(f)


def output_options(f: F) -> F:
    f = click.option(
        "--log-level",
        type=click.Choice(
            [level.lower() for level in ALL_LOG_LEVELS],
            case_sensitive=False,
        ),
        default=DEFAULT_LOG_LEVEL,
        envvar="INSPECT_FLOW_LOG_LEVEL",
        help="Set the log level (defaults to `'warning'`).",
    )(f)
    f = click.option(
        "--display",
        type=click.Choice(
            ["full", "rich", "plain"],
            case_sensitive=False,
        ),
        default="rich",
        envvar="INSPECT_FLOW_DISPLAY",
        help="Set the display mode (defaults to `'rich'`).",
    )(f)
    return f


def base_config_options(f: F) -> F:
    """Shared options for commands that load a flow config."""
    f = output_options(f)
    f = click.argument(
        "config-file",
        type=click.Path(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
        required=True,
    )(f)
    f = click.option(
        "--set",
        "-s",
        multiple=True,
        type=str,
        envvar="INSPECT_FLOW_SET",
        help="""
    Override any field in the flow config using dot notation (e.g. `field.subfield=value`).
    The path corresponds to the fields of `FlowSpec` and its nested types
    (`options`, `defaults`, `tasks`, etc.).

    Examples:
      `--set options.limit=10`
      `--set defaults.solver.args.tool_calls=none`
      `--set options.metadata={"key1": "val1", "key2": "val2"}`

    Values are parsed as JSON when possible (lists and dicts), otherwise as strings.
    String values are appended to existing lists; JSON lists and dicts replace existing values.
    When the same key is provided multiple times, later values override earlier ones.
    """,
    )(f)
    f = click.option(
        "--arg",
        "-A",
        multiple=True,
        type=str,
        envvar="INSPECT_FLOW_ARG",
        help="""
    Set arguments that will be passed as kwargs to the function in the flow config. Only used when the last statement in the config file is a function.

    Examples:
      `--arg task_min_priority=2`

    If the same key is provided multiple times, later values will override earlier ones.
    """,
    )(f)
    f = click.option(
        "--log-dir",
        type=click.Path(
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
            resolve_path=False,
        ),
        default=None,
        help="Set the log directory. Will override the `log_dir` specified in the config.",
        envvar="INSPECT_FLOW_LOG_DIR",
    )(f)
    return f


def check_options(f: F) -> F:
    """Options for the check command."""
    f = base_config_options(f)
    f = click.option(
        "--limit",
        type=int,
        default=None,
        help="Set the expected number of samples per task for completeness calculation.",
        envvar="INSPECT_FLOW_LIMIT",
    )(f)
    f = click.option(
        "--venv",
        type=bool,
        is_flag=True,
        help="If set, resolve tasks in a virtual environment in a temporary directory.",
        envvar="INSPECT_FLOW_VENV",
    )(f)
    return f


def config_options(f: F) -> F:
    """Options for overriding the config."""
    f = base_config_options(f)
    f = click.option(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of samples to run.",
        envvar="INSPECT_FLOW_LIMIT",
    )(f)
    f = store_option(
        f,
        help="Path to the store directory. Will override the store specified in the config. `'auto'` for default location. `'none'` for no store.",
    )
    f = click.option(
        "--store-filter",
        type=str,
        multiple=True,
        help="Log filter to apply when searching the store for existing logs. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass).",
        envvar="INSPECT_FLOW_STORE_FILTER",
    )(f)
    f = click.option(
        "--store-read/--no-store-read",
        default=None,
        help="Read existing logs from the store (default: `--no-store-read`).",
        envvar="INSPECT_FLOW_STORE_READ",
    )(f)
    f = click.option(
        "--store-write/--no-store-write",
        default=None,
        help="Write completed logs to the store (default: `--store-write`).",
        envvar="INSPECT_FLOW_STORE_WRITE",
    )(f)
    f = click.option(
        "--log-dir-create-unique/--no-log-dir-create-unique",
        default=None,
        help="If set, create a unique log directory by appending a datetime subdirectory (e.g. `2025-12-09T17-36-43`) under the specified `log_dir`. If not set, use the existing `log_dir` (which must be empty or have `log_dir_allow_dirty=True`).",
        envvar="INSPECT_FLOW_LOG_DIR_CREATE_UNIQUE",
    )(f)
    f = click.option(
        "--resume",
        type=bool,
        is_flag=True,
        help="Resume from the previous run by reusing its log directory. Mutually exclusive with `--log-dir`.",
        envvar="INSPECT_FLOW_RESUME",
    )(f)
    f = click.option(
        "--venv",
        type=bool,
        is_flag=True,
        help="If set run the flow in a virtual environment in a temporary directory.",
        envvar="INSPECT_FLOW_VENV",
    )(f)
    return f


class OutputOptionArgs(TypedDict, total=False):
    log_level: str
    display: DisplayType


class BaseConfigOptionArgs(OutputOptionArgs, total=False):
    log_dir: str | None
    set: list[str] | None
    arg: list[str] | None


class CheckOptionArgs(BaseConfigOptionArgs, total=False):
    limit: int | None
    venv: bool | None


class ConfigOptionArgs(CheckOptionArgs, total=False):
    store: str | None
    store_filter: tuple[str, ...]
    store_read: bool | None
    store_write: bool | None
    log_dir_allow_dirty: bool | None
    log_dir_create_unique: bool | None
    resume: bool | None


def init_output(**kwargs: Unpack[OutputOptionArgs]) -> None:
    log_level = kwargs.get("log_level", DEFAULT_LOG_LEVEL)
    init_flow_logging(log_level)
    display = kwargs.get("display", "rich")
    set_display_type(display)


def _options_to_overrides(**kwargs: Unpack[ConfigOptionArgs]) -> list[str]:
    overrides = list(kwargs.get("set") or [])  # set may be a tuple (at least in tests)
    if store := kwargs.get("store"):
        if store.lower() not in ("auto", "none"):
            store = absolute_file_path(store)
        overrides.append(f"store={store}")
    if log_dir := kwargs.get("log_dir"):
        log_dir = absolute_file_path(log_dir)
        overrides.append(f"log_dir={log_dir}")
    if limit := kwargs.get("limit"):
        overrides.append(f"options.limit={limit}")
    if (ldu := kwargs.get("log_dir_create_unique")) is not None:
        overrides.append(f"log_dir_create_unique={ldu}")
    if kwargs.get("log_dir_allow_dirty"):
        overrides.append("options.log_dir_allow_dirty=True")
    if kwargs.get("venv"):
        overrides.append("execution_type=venv")
    return overrides


def _options_to_args(**kwargs: Unpack[BaseConfigOptionArgs]) -> dict[str, Any]:
    args = list(kwargs.get("arg") or [])  # arg may be a tuple (at least in tests)
    return parse_cli_args(args)


def parse_config_options(**kwargs: Unpack[ConfigOptionArgs]) -> ConfigOptions:
    resume = bool(kwargs.get("resume"))
    if resume and kwargs.get("log_dir"):
        raise click.UsageError("--resume and --log-dir are mutually exclusive.")
    return ConfigOptions(
        overrides=_options_to_overrides(**kwargs),
        args=_options_to_args(**kwargs),
        resume=resume,
        store_filter=kwargs.get("store_filter") or None,
        store_read=kwargs.get("store_read"),
        store_write=kwargs.get("store_write"),
    )
