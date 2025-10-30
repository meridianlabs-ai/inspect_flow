import os

import click

from inspect_flow._config.config import load_config
from inspect_flow._submit.submit import submit


@click.command("submit", help="Submit a job")
@click.argument("config-file", type=str, required=True)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run eval, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
def submit_command(
    config_file: str,
    dry_run: bool,
) -> None:
    if dry_run:
        os.environ["INSPECT_FLOW_DRY_RUN"] = "1"
    config = load_config(config_file)
    submit(config, config_file)
