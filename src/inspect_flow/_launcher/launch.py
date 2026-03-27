from logging import getLogger

from inspect_flow._api.api import CheckResult
from inspect_flow._launcher.inproc import inproc_check, inproc_launch
from inspect_flow._launcher.venv import venv_check, venv_launch
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.data import LAST_LOG_DIR_KEY, write_data
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


def launch(spec: FlowSpec, base_dir: str, dry_run: bool = False) -> None:
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

    if spec.execution_type == "venv":
        venv_launch(spec=spec, base_dir=base_dir, dry_run=dry_run)
    else:
        inproc_launch(spec=spec, base_dir=base_dir, dry_run=dry_run)


def launch_check(spec: FlowSpec, base_dir: str) -> CheckResult | None:
    if not spec.log_dir:
        raise ValueError("log_dir must be set before checking the flow spec")
    spec.log_dir = absolute_path_relative_to(spec.log_dir, base_dir=base_dir)

    if spec.execution_type == "venv":
        return venv_check(spec=spec, base_dir=base_dir)
    else:
        return inproc_check(spec=spec, base_dir=base_dir)
