from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._display.display import DisplayAction, LiveDisplay
from inspect_flow._launcher.launch import launch
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging

_run_actions = [
    DisplayAction(key="load", description="Load config"),
    DisplayAction(key="env", description="Set up environment"),
    DisplayAction(key="instantiate", description="Instantiate tasks"),
    DisplayAction(key="logs", description="Check for existing logs"),
    DisplayAction(key="evalset", description="Run evalset"),
]


@click.command("run", help="Run a spec")
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run spec, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
@click.option(
    "--log-dir-allow-dirty",
    type=bool,
    is_flag=True,
    help="Do not fail if the log-dir contains files that are not part of the eval set.",
    envvar="INSPECT_FLOW_LOG_DIR_ALLOW_DIRTY",
)
@config_options
def run_command(
    config_file: str,
    dry_run: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to run a spec."""
    log_level = kwargs.get("log_level", DEFAULT_LOG_LEVEL)
    init_flow_logging(log_level)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    with LiveDisplay(dry_run=dry_run, actions=_run_actions):
        spec = int_load_spec(config_file, options=config_options)
        launch(
            spec,
            base_dir=str(Path(config_file).parent),
            dry_run=dry_run,
            no_dotenv=False,
        )
