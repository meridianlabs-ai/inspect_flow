import sys
from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.json_output import emit_json, output_context
from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    init_output,
    json_option,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._display.display import DisplayAction, DisplayMode
from inspect_flow._launcher.launch import launch, launch_dry_run
from inspect_flow._runner.cli import RUN_ACTIONS
from inspect_flow._util.constants import EXIT_INCOMPLETE

_run_actions = {
    "load": DisplayAction(description="Load config"),
    "env": DisplayAction(description="Set up environment"),
} | RUN_ACTIONS


@click.command("run", help="Run a spec")
@json_option
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run spec, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
@click.option(
    "--log-dir-allow-dirty",
    type=bool,
    is_flag=True,
    help="Do not fail if the `log-dir` contains files that are not part of the eval set.",
    envvar="INSPECT_FLOW_LOG_DIR_ALLOW_DIRTY",
)
@click.option(
    "--handle-file",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=False,
    ),
    default=None,
    help="Write a JSON launch handle (with the run's `log_dir` and `pid`) to this file once the log directory is resolved. Lets a monitor discover a backgrounded run.",
    envvar="INSPECT_FLOW_HANDLE_FILE",
)
@config_options
def run_command(
    config_file: str,
    output_json: bool,
    dry_run: bool,
    handle_file: str | None,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to run a spec."""
    init_output(**kwargs)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    base_dir = str(Path(config_file).parent)
    if handle_file is not None:
        handle_file = absolute_file_path(handle_file)
    if output_json and not dry_run:
        raise click.UsageError("--json is only supported with --dry-run.")
    mode: DisplayMode = "dry_run" if dry_run else "run"
    with output_context(
        output_json, mode=mode, actions=_run_actions, config_file=config_file
    ):
        spec = int_load_spec(config_file, options=config_options)
        json_result = launch_dry_run(spec, base_dir=base_dir) if output_json else None
        result = (
            None
            if output_json
            else launch(
                spec, base_dir=base_dir, dry_run=dry_run, handle_file=handle_file
            )
        )
    if output_json:
        assert json_result is not None
        emit_json(json_result)
        return
    assert result is not None
    if not dry_run and not result.success:
        sys.exit(EXIT_INCOMPLETE)
