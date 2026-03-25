from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    init_output,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._display.display import DisplayAction, create_display
from inspect_flow._launcher.launch import launch_check
from inspect_flow._runner.cli import CHECK_ACTIONS
from inspect_flow._util.console import path

_check_actions = {
    "load": DisplayAction(description="Load config"),
    "env": DisplayAction(description="Set up environment"),
} | CHECK_ACTIONS


@click.command("check", help="Check a spec against existing logs")
@config_options
def check_command(
    config_file: str,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to check a spec against existing logs."""
    init_output(**kwargs)
    config_file = absolute_file_path(config_file)
    with create_display(dry_run=True, actions=_check_actions) as display:
        display.set_title("Flow Spec:", path(config_file))
        spec = int_load_spec(config_file, options=parse_config_options(**kwargs))
        launch_check(spec, base_dir=str(Path(config_file).parent))
