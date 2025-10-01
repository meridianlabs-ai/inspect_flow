import click


@click.command("submit", help="Submit a job")
@click.argument("config-file", type=str, required=True)
def submit_command(
    config_file: str,
) -> None:
    pass
