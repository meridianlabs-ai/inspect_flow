import os
from logging import getLogger

from inspect_flow._display.run_action import RunAction
from inspect_flow._launcher.freeze import write_flow_requirements
from inspect_flow._runner.check import check_eval_set
from inspect_flow._runner.logs import FindLogsResult
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.flow_types import FlowSpec

logger = getLogger(__name__)


def inproc_launch(spec: FlowSpec, base_dir: str, dry_run: bool) -> None:
    with RunAction("env", info="inproc"):
        if spec.env:
            os.environ.update(spec.env)

        write_flow_requirements(spec, cwd=".", env=os.environ.copy(), dry_run=dry_run)
    run_eval_set(spec, base_dir=base_dir, dry_run=dry_run)


def inproc_check(spec: FlowSpec, base_dir: str) -> FindLogsResult:
    with RunAction("env", info="inproc"):
        if spec.env:
            os.environ.update(spec.env)
    return check_eval_set(spec, base_dir=base_dir)
