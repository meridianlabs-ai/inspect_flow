import click

from inspect_flow._submit.submit import submit


@click.command("submit", help="Submit a job")
@click.argument("config-file", type=str, required=True)
def submit_command(
    config_file: str,
) -> None:
    submit(config_file)
