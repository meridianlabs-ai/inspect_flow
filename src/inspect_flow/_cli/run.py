import click
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    options_to_overrides,
)
from inspect_flow._config.config import load_config
from inspect_flow._launcher.launch import submit


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
    overrides = options_to_overrides(**kwargs)
    config = load_config(config_file, overrides=overrides)

    run_args = ["--dry-run"] if dry_run else []
    submit(config, config_file, run_args)
