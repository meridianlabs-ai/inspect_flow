import click
from typing_extensions import Unpack

from inspect_flow._api.api import run
from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    parse_config_options,
)
from inspect_flow._config.load import load_config


@click.command("run", help="Run a job")
@click.argument("config-file", type=str, required=True)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run eval, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
@config_options
def run_command(
    config_file: str,
    dry_run: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    config_options = parse_config_options(**kwargs)
    config = load_config(config_file, config_options=config_options)
    run(config, dry_run=dry_run)
