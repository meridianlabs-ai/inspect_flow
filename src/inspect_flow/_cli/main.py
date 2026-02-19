import sys

import click
from dotenv import find_dotenv, load_dotenv

from inspect_flow._cli.config import config_command
from inspect_flow._cli.store import store_command
from inspect_flow._util.console import flow_print
from inspect_flow._util.error import set_exception_hook

from .. import __version__
from .run import run_command


@click.group(invoke_without_command=True, context_settings={"max_content_width": 120})
@click.option(
    "--version",
    type=bool,
    is_flag=True,
    default=False,
    help="Print the flow version.",
)
@click.pass_context
def flow(
    ctx: click.Context,
    version: bool,
) -> None:
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    if version:
        click.echo(__version__)
        ctx.exit()
    else:
        click.echo(ctx.get_help())
        ctx.exit()


flow.add_command(run_command)
flow.add_command(config_command)
flow.add_command(store_command)


def main() -> None:  # pragma: no cover
    set_exception_hook()
    load_dotenv(find_dotenv(usecwd=True))
    try:
        flow(auto_envvar_prefix="INSPECT_FLOW", standalone_mode=False)
    except click.ClickException as e:
        if isinstance(e, click.UsageError) and e.ctx:
            flow_print("")
            flow_print(e.ctx.get_usage())
            if e.ctx.command.get_help_option(e.ctx) is not None:
                flow_print(
                    f"Try '{e.ctx.command_path} {e.ctx.help_option_names[0]}' for help."
                )

        flow_print("\n[red]Error:[/red]", e.format_message(), format="error")
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
