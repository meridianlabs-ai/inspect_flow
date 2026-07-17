from logging import getLogger
from typing import Any, NamedTuple

from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import filesystem

from inspect_flow._launcher.inproc import (
    inproc_check,
    inproc_dry_run,
    inproc_launch,
)
from inspect_flow._launcher.venv import venv_check, venv_dry_run_json, venv_launch
from inspect_flow._runner.logs import FindLogsResult, find_logs_result_to_json
from inspect_flow._runner.run import LaunchResult
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.data import LAST_LOG_DIR_KEY, write_data
from inspect_flow._util.path_util import absolute_path_relative_to
from inspect_flow._util.run_handle import write_run_handle

logger = getLogger(__name__)


class CheckLaunchResult(NamedTuple):
    is_complete: bool
    find_result: FindLogsResult | None
    json_result: dict[str, Any] | None = None


def _prepare_launch_spec(spec: FlowSpec, base_dir: str) -> None:
    if not spec.log_dir:
        raise ValueError("log_dir must be set before launching the flow spec")
    spec.log_dir = absolute_path_relative_to(spec.log_dir, base_dir=base_dir)

    write_data(LAST_LOG_DIR_KEY, spec.log_dir)

    if spec.options and spec.options.bundle_dir:
        # Ensure bundle_dir and bundle_url_mappings are absolute paths
        spec.options.bundle_dir = absolute_path_relative_to(
            spec.options.bundle_dir, base_dir=base_dir
        )
        if spec.options.bundle_url_mappings:
            spec.options.bundle_url_mappings = {
                absolute_path_relative_to(k, base_dir=base_dir): v
                for k, v in spec.options.bundle_url_mappings.items()
            }

    if spec.options and isinstance(spec.options.scanner, str):
        scanner_path = absolute_path_relative_to(
            spec.options.scanner, base_dir=base_dir
        )
        # fail fast on a typo'd path rather than after the venv build
        if not filesystem(scanner_path).exists(scanner_path):
            raise PrerequisiteError(
                f"Scanner config file '{scanner_path}' does not exist."
            )
        spec.options.scanner = scanner_path


def launch(
    spec: FlowSpec,
    base_dir: str,
    dry_run: bool = False,
    handle_file: str | None = None,
) -> LaunchResult:
    _prepare_launch_spec(spec, base_dir=base_dir)
    if handle_file and not dry_run:
        assert spec.log_dir
        write_run_handle(
            absolute_path_relative_to(handle_file, base_dir=base_dir), spec.log_dir
        )
    if spec.execution_type == "venv":
        return venv_launch(spec=spec, base_dir=base_dir, dry_run=dry_run)
    else:
        return inproc_launch(spec=spec, base_dir=base_dir, dry_run=dry_run)


def launch_dry_run(spec: FlowSpec, base_dir: str) -> dict[str, Any] | None:
    _prepare_launch_spec(spec, base_dir=base_dir)
    assert spec.log_dir
    if spec.execution_type == "venv":
        return venv_dry_run_json(spec=spec, base_dir=base_dir)
    return find_logs_result_to_json(
        inproc_dry_run(spec=spec, base_dir=base_dir), spec.log_dir
    )


def launch_check(
    spec: FlowSpec, base_dir: str, output_json: bool = False
) -> CheckLaunchResult:
    if not spec.log_dir:
        raise ValueError("log_dir must be set before checking the flow spec")
    spec.log_dir = absolute_path_relative_to(spec.log_dir, base_dir=base_dir)

    if spec.execution_type == "venv":
        # The full result lives in the subprocess; the completeness flag (and the
        # JSON result under --json) are signaled back via a per-run result file.
        result = venv_check(spec=spec, base_dir=base_dir, output_json=output_json)
        return CheckLaunchResult(
            is_complete=result.ok, find_result=None, json_result=result.json_result
        )
    else:
        result = inproc_check(spec=spec, base_dir=base_dir)
        json_result = (
            find_logs_result_to_json(result, spec.log_dir) if output_json else None
        )
        return CheckLaunchResult(
            is_complete=result.is_complete,
            find_result=result,
            json_result=json_result,
        )
