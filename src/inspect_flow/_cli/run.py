import click

from inspect_flow._config.config import load_config
from inspect_flow._submit.submit import submit


@click.command("run", help="Run a job")
@click.argument("config-file", type=str, required=True)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run eval, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
def run_command(
    config_file: str,
    dry_run: bool,
) -> None:
    run_args = ["--dry-run"] if dry_run else []
    config = load_config(config_file)
    submit(config, config_file, run_args)
