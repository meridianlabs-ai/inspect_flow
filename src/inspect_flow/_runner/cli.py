from __future__ import annotations

import click
import yaml

from inspect_flow._display.display import (
    DisplayAction,
    DisplayType,
    create_display,
    set_display_type,
)
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.console import path
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.error import set_exception_hook
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.subprocess_util import signal_ready_and_wait

VENV_ACTIONS = {
    "instantiate": DisplayAction(description="Instantiate tasks"),
    "logs": DisplayAction(description="Check for existing logs"),
    "evalset": DisplayAction(description="Run evalset"),
}


def _read_config(config_file: str) -> FlowSpec:
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        return FlowSpec.model_validate(data, extra="forbid")


@click.group(invoke_without_command=True)
@click.option(
    "--file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
)
@click.option(
    "--base-dir",
    type=str,
    default="",
    help="Base directory.",
)
@click.option(
    "--log-level",
    type=str,
    default=DEFAULT_LOG_LEVEL,
    help="Log level.",
)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    default=False,
    help="Dry run.",
)
@click.option(
    "--display",
    "display_type",
    type=click.Choice(["full", "rich", "plain"]),
    default="rich",
    help="Display type.",
)
@click.pass_context
def flow_run(
    ctx: click.Context,
    file: str,
    base_dir: str,
    log_level: str,
    dry_run: bool,
    display_type: DisplayType,
) -> None:
    set_exception_hook()

    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        raise NotImplementedError("Run has no subcommands.")

    init_flow_logging(log_level=log_level)
    signal_ready_and_wait()

    set_display_type(display_type)
    cfg = _read_config(file)
    with create_display(dry_run=dry_run, actions=VENV_ACTIONS) as display:
        display.set_title("VENV Flow Spec:", path(file))
        run_eval_set(cfg, base_dir=base_dir, dry_run=dry_run)


if __name__ == "__main__":
    flow_run()
