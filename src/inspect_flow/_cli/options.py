from typing import Any

import click
from inspect_ai._cli.util import parse_cli_args
from inspect_ai._util.constants import (
    ALL_LOG_LEVELS,
)
from typing_extensions import TypedDict, Unpack

from inspect_flow._config.load import ConfigOptions


def log_level_option(f):
    f = click.option(
        "--log-level",
        type=click.Choice(
            [level.lower() for level in ALL_LOG_LEVELS],
            case_sensitive=False,
        ),
        default="info",
        envvar="INSPECT_FLOW_LOG_LEVEL",
        help="Set the log level (defaults to 'info')",
    )(f)
    return f


def config_options(f):
    """Options for overriding the config."""
    f = log_level_option(f)
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
    Set config overrides.

    Examples:
      `--set defaults.solver.args.tool_calls=none`
      `--set options.limit=10`
      `--set options.metadata={"key1": "val1", "key2": "val2"}`

    The specified value may be a string or json parsable list or dict.
    If string is provided then it will be appended to existing list values.
    If json list or dict is provided then it will replace existing values.
    If the same key is provided multiple times, later values will override earlier ones.
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
        "--limit",
        type=int,
        default=None,
        help="Limit the number of samples to run.",
        envvar="INSPECT_FLOW_LIMIT",
    )(f)
    f = click.option(
        "--log-dir",
        type=click.Path(
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
            resolve_path=True,
        ),
        default=None,
        help="Set the log directory. Will override the log_dir specified in the config.",
        envvar="INSPECT_FLOW_LOG_DIR",
    )(f)
    f = click.option(
        "--log-dir-create-unique",
        type=bool,
        is_flag=True,
        help="If set, create a new log directory by appending an _ and numeric suffix if the specified log_dir already exists. If the directory exists and has a _numeric suffix, that suffix will be incremented. If not set, use the existing log_dir (which must be empty or have log_dir_allow_dirty=True).",
        envvar="INSPECT_FLOW_LOG_DIR_CREATE_UNIQUE",
    )(f)
    f = click.option(
        "--no-venv",
        type=bool,
        is_flag=True,
        help="If set run the flow in the current environment without creating a virtual environment.",
        envvar="INSPECT_FLOW_NO_VENV",
    )(f)
    return f


class ConfigOptionArgs(TypedDict, total=False):
    log_level: str | None
    log_dir: str | None
    log_dir_create_unique: bool | None
    limit: int | None
    set: list[str] | None
    arg: list[str] | None
    no_venv: bool | None


def _options_to_overrides(**kwargs: Unpack[ConfigOptionArgs]) -> list[str]:
    overrides = list(kwargs.get("set") or [])  # set may be a tuple (at least in tests)
    if log_dir := kwargs.get("log_dir"):
        overrides.append(f"log_dir={log_dir}")
    if limit := kwargs.get("limit"):
        overrides.append(f"options.limit={limit}")
    if kwargs.get("log_dir_create_unique"):
        overrides.append("log_dir_create_unique=True")
    return overrides


def _options_to_args(**kwargs: Unpack[ConfigOptionArgs]) -> dict[str, Any]:
    args = list(kwargs.get("arg") or [])  # arg may be a tuple (at least in tests)
    return parse_cli_args(args)


def parse_config_options(**kwargs: Unpack[ConfigOptionArgs]) -> ConfigOptions:
    return ConfigOptions(
        overrides=_options_to_overrides(**kwargs),
        args=_options_to_args(**kwargs),
    )
