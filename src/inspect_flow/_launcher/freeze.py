from pathlib import Path

from inspect_ai._util.file import file, filesystem

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.subprocess_util import run_with_logging


def write_flow_requirements(
    spec: FlowSpec, cwd: str, env: dict[str, str], dry_run: bool
) -> None:
    # Freeze installed packages to flow-requirements.txt in log_dir
    if not dry_run and spec.log_dir:
        freeze_result = run_with_logging(
            ["uv", "pip", "freeze"],
            cwd=cwd,
            env=env,
            log_output=False,  # Don't log the full freeze output
        )
        requirements_in = Path(cwd) / "flow-requirements.in"
        with open(requirements_in, "w") as f:
            f.write(freeze_result.stdout)

        try:
            compile_result = run_with_logging(
                [
                    "uv",
                    "pip",
                    "compile",
                    "--generate-hashes",
                    "--no-header",
                    "--no-annotate",
                    str(requirements_in),
                ],
                cwd=cwd,
                env=env,
                log_output=False,
            )
        finally:
            requirements_in.unlink()

        fs = filesystem(spec.log_dir)
        fs.mkdir(spec.log_dir, exist_ok=True)
        with file(spec.log_dir + "/flow-requirements.txt", "w") as f:
            f.write(compile_result.stdout)
