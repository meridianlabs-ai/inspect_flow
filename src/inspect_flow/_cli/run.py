from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.json_output import (
    emit_json,
    ensure_json_supported,
    find_logs_result_to_json,
    quiet_output,
)
from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    init_output,
    json_option,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._display.display import DisplayAction, DisplayMode, create_display
from inspect_flow._launcher.launch import launch, launch_dry_run
from inspect_flow._runner.cli import RUN_ACTIONS
from inspect_flow._util.console import path

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
@config_options
def run_command(
    config_file: str,
    output_json: bool,
    dry_run: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to run a spec."""
    init_output(**kwargs)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    base_dir = str(Path(config_file).parent)
    if output_json:
        if not dry_run:
            raise click.UsageError("--json is only supported with --dry-run.")
        with quiet_output():
            spec = int_load_spec(config_file, options=config_options)
            ensure_json_supported(spec)
            result = launch_dry_run(spec, base_dir=base_dir)
        assert spec.log_dir
        assert result is not None
        emit_json(find_logs_result_to_json(result, spec.log_dir))
        return
    mode: DisplayMode = "dry_run" if dry_run else "run"
    with create_display(mode=mode, actions=_run_actions) as display:
        display.set_title("Flow Spec:", path(config_file))
        spec = int_load_spec(config_file, options=config_options)
        launch(
            spec,
            base_dir=base_dir,
            dry_run=dry_run,
        )
