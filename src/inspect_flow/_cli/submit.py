import click

from inspect_flow._config.config import load_config
from inspect_flow._submit.submit import submit


@click.command("submit", help="Submit a job")
@click.argument("config-file", type=str, required=True)
def submit_command(
    config_file: str,
) -> None:
    config = load_config(config_file)
    submit(config)
