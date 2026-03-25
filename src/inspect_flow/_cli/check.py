from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    OutputOptionArgs,
    init_output,
    output_options,
)
from inspect_flow._config.load import ConfigOptions, int_load_spec
from inspect_flow._display.display import DisplayAction, create_display
from inspect_flow._launcher.launch import launch_check
from inspect_flow._runner.cli import CHECK_ACTIONS
from inspect_flow._util.console import path

_check_actions = {
    "load": DisplayAction(description="Load config"),
    "env": DisplayAction(description="Set up environment"),
} | CHECK_ACTIONS


@click.command("check", help="Check a spec against existing logs")
@click.argument(
    "config-file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    required=True,
)
@click.option(
    "--log-dir",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
    ),
    default=None,
    help="Log directory to check against. Overrides `log_dir` in the spec.",
    envvar="INSPECT_FLOW_LOG_DIR",
)
@click.option(
    "--venv",
    type=bool,
    is_flag=True,
    help="Run in a virtual environment.",
    envvar="INSPECT_FLOW_VENV",
)
@output_options
def check_command(
    config_file: str,
    log_dir: str | None,
    venv: bool,
    **kwargs: Unpack[OutputOptionArgs],
) -> None:
    """CLI command to check a spec against existing logs."""
    init_output(**kwargs)
    overrides: list[str] = []
    if log_dir:
        overrides.append(f"log_dir={absolute_file_path(log_dir)}")
    if venv:
        overrides.append("execution_type=venv")
    with create_display(dry_run=True, actions=_check_actions) as display:
        display.set_title("Flow Spec:", path(config_file))
        spec = int_load_spec(config_file, options=ConfigOptions(overrides=overrides))
        launch_check(spec, base_dir=str(Path(config_file).parent))
