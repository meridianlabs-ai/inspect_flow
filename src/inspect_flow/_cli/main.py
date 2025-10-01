import click
from dotenv import load_dotenv

from .. import __version__
from .submit import submit_command


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    type=bool,
    is_flag=True,
    default=False,
    help="Print the flow version.",
)
@click.pass_context
def flow(ctx: click.Context, version: bool) -> None:
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    if version:
        print(__version__)
        ctx.exit()
    else:
        click.echo(ctx.get_help())
        ctx.exit()


flow.add_command(submit_command)


def main() -> None:
    load_dotenv()
    flow(auto_envvar_prefix="FLOW")  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
