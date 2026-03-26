from __future__ import annotations

import click
import yaml

from inspect_flow._display.display import (
    DisplayAction,
    DisplayMode,
    DisplayType,
    create_display,
    set_display_type,
)
from inspect_flow._runner.check import check_eval_set
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.console import path
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.error import set_exception_hook
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.subprocess_util import signal_ready_and_wait

RUN_ACTIONS = {
    "instantiate": DisplayAction(description="Instantiate tasks"),
    "logs": DisplayAction(description="Check for existing logs"),
    "evalset": DisplayAction(description="Run evalset"),
}

CHECK_ACTIONS = {
    "instantiate": DisplayAction(description="Instantiate tasks"),
    "logs": DisplayAction(description="Check for existing logs"),
}


def _read_config(config_file: str) -> FlowSpec:
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        return FlowSpec.model_validate(data, extra="forbid")


def _common_options(fn: click.decorators.FC) -> click.decorators.FC:
    fn = click.option(
        "--file",
        type=click.Path(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    )(fn)
    fn = click.option(
        "--base-dir",
        type=str,
        default="",
        help="Base directory.",
    )(fn)
    fn = click.option(
        "--log-level",
        type=str,
        default=DEFAULT_LOG_LEVEL,
        help="Log level.",
    )(fn)
    fn = click.option(
        "--display",
        "display_type",
        type=click.Choice(["full", "rich", "plain"]),
        default="rich",
        help="Display type.",
    )(fn)
    return fn


@click.group()
def runner() -> None:
    pass


@runner.command("run")
@_common_options
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    default=False,
    help="Dry run.",
)
def runner_run(
    file: str,
    base_dir: str,
    log_level: str,
    display_type: DisplayType,
    dry_run: bool,
) -> None:
    set_exception_hook()
    init_flow_logging(log_level=log_level)
    signal_ready_and_wait()
    set_display_type(display_type)
    cfg = _read_config(file)
    mode: DisplayMode = "dry_run" if dry_run else "run"
    with create_display(mode=mode, actions=RUN_ACTIONS) as disp:
        disp.set_title("VENV Flow Spec:", path(file))
        run_eval_set(cfg, base_dir=base_dir, dry_run=dry_run)


@runner.command("check")
@_common_options
def runner_check(
    file: str,
    base_dir: str,
    log_level: str,
    display_type: DisplayType,
) -> None:
    set_exception_hook()
    init_flow_logging(log_level=log_level)
    signal_ready_and_wait()
    set_display_type(display_type)
    cfg = _read_config(file)
    with create_display(mode="check", actions=CHECK_ACTIONS) as disp:
        disp.set_title("VENV Flow Spec:", path(file))
        check_eval_set(cfg, base_dir=base_dir)


if __name__ == "__main__":
    runner()
