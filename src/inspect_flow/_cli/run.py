import click

from inspect_flow._config.config import load_config
from inspect_flow._submit.submit import submit


class SubcommandWithParentHelp(click.Command):
    def format_help(self, ctx, formatter):
        # First, format the subcommand's own help
        super().format_help(ctx, formatter)

        # Then add parent options if they exist
        if ctx.parent and ctx.parent.command:
            # Get parent command's options
            parent_opts = [
                param
                for param in ctx.parent.command.params
                if isinstance(param, click.Option) and param.name != "version"
            ]

            help_records = [opt.get_help_record(ctx.parent) for opt in parent_opts]
            help_records = [help_record for help_record in help_records if help_record]

            with formatter.section("Parent Options (use before 'run')"):
                formatter.write_dl(
                    [(help_record[0], help_record[1]) for help_record in help_records]
                )


@click.command("run", help="Run a job", cls=SubcommandWithParentHelp)
@click.argument("config-file", type=str, required=True)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run eval, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
@click.pass_context
def run_command(
    ctx: click.Context,
    config_file: str,
    dry_run: bool,
) -> None:
    # Get parent options from context
    assert ctx.parent is not None
    # flow_dir = ctx.parent.params.get("flow_dir")
    # limit = ctx.parent.params.get("limit")
    # set_options = ctx.parent.params.get("set")

    run_args = ["--dry-run"] if dry_run else []
    config = load_config(config_file)
    submit(config, config_file, run_args)
