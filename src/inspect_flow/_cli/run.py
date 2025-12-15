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
from inspect_flow._launcher.launch import launch
from inspect_flow._util.logging import init_flow_logging


@click.command("run", help="Run a spec")
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run spec, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
@config_options
def run_command(
    config_file: str,
    dry_run: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to run a spec."""
    log_level = kwargs.get("log_level")
    init_flow_logging(log_level)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    spec = int_load_spec(config_file, options=config_options)
    launch(
        spec,
        base_dir=str(Path(config_file).parent),
        dry_run=dry_run,
        no_venv=kwargs.get("no_venv", False) or False,
        no_dotenv=False,
    )
