import click
from dotenv import find_dotenv, load_dotenv

from inspect_flow._cli.config import config_command

from .. import __version__
from .run import run_command


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    type=bool,
    is_flag=True,
    default=False,
    help="Print the flow version.",
)
@click.option(
    "--flow-dir",
    type=str,
    default=None,
    help="Override the flow directory specified in the config.",
    envvar="INSPECT_FLOW_DIR",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit the number of tasks to run.",
    envvar="INSPECT_FLOW_LIMIT",
)
@click.option(
    "--set",
    "-s",
    multiple=True,
    type=str,
    help="Set config overrides, e.g. 'defaults/solver/args/tool_calls=none'",
)
@click.pass_context
def flow(
    ctx: click.Context,
    version: bool,
    flow_dir: str | None,
    limit: int | None,
    set: list[str],
) -> None:
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    if version:
        print(__version__)
        ctx.exit()
    else:
        click.echo(ctx.get_help())
        ctx.exit()


flow.add_command(run_command)
flow.add_command(config_command)


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True))
    flow(auto_envvar_prefix="INSPECT_FLOW")


if __name__ == "__main__":
    main()
