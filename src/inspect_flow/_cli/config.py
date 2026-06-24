import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.json_output import emit_json, quiet_output
from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    init_output,
    json_option,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._config.write import print_config_yaml
from inspect_flow._util.pydantic_util import model_dump


@click.command("config", help="Output config")
@json_option
@config_options
def config_command(
    config_file: str,
    output_json: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to output config."""
    init_output(**kwargs)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    if output_json:
        with quiet_output():
            fconfig = int_load_spec(config_file, options=config_options)
        emit_json(model_dump(fconfig))
        return
    fconfig = int_load_spec(config_file, options=config_options)
    print_config_yaml(fconfig, resolved=False)
