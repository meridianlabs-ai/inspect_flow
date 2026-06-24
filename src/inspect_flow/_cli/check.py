import sys
from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.json_output import (
    emit_json,
    find_logs_result_to_json,
    quiet_output,
)
from inspect_flow._cli.options import (
    ConfigOptionArgs,
    check_options,
    init_output,
    json_option,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._display.display import DisplayAction, create_display
from inspect_flow._launcher.launch import launch_check
from inspect_flow._runner.cli import CHECK_ACTIONS
from inspect_flow._util.console import path
from inspect_flow._util.constants import EXIT_INCOMPLETE

_check_actions = {
    "load": DisplayAction(description="Load config"),
    "env": DisplayAction(description="Set up environment"),
} | CHECK_ACTIONS


@click.command(
    "check",
    help="Check a spec against existing logs (searches log directory recursively)",
)
@json_option
@check_options
def check_command(
    config_file: str,
    output_json: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    init_output(**kwargs)
    config_file = absolute_file_path(config_file)
    kwargs["log_dir_create_unique"] = False
    base_dir = str(Path(config_file).parent)
    if output_json:
        with quiet_output():
            spec = int_load_spec(config_file, options=parse_config_options(**kwargs))
            result = launch_check(spec, base_dir=base_dir)
        assert spec.log_dir
        emit_json(
            find_logs_result_to_json(result.find_result, spec.log_dir)
            if result.find_result is not None
            else None
        )
        if not result.is_complete:
            sys.exit(EXIT_INCOMPLETE)
        return
    with create_display(mode="check", actions=_check_actions) as display:
        display.set_title("Flow Spec:", path(config_file))
        spec = int_load_spec(config_file, options=parse_config_options(**kwargs))
        result = launch_check(spec, base_dir=base_dir)
    if not result.is_complete:
        sys.exit(EXIT_INCOMPLETE)
