import click

from inspect_flow._client.client import Client


@click.command("submit", help="Submit a job")
@click.argument("config-file", type=str, required=True)
def submit_command(
    config_file: str,
) -> str:
    client = Client()
    client.set_config(config_file)
    return client.submit()
