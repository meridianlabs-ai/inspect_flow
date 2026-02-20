import logging
import subprocess
from pathlib import Path

from inspect_ai._util.file import file, filesystem

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.subprocess_util import run_with_logging

logger = logging.getLogger(__name__)


def write_flow_requirements(
    spec: FlowSpec, cwd: str, env: dict[str, str], dry_run: bool
) -> None:
    if dry_run or not spec.log_dir:
        return
    # Freeze installed packages to flow-requirements.txt in log_dir
    freeze_result = run_with_logging(
        ["uv", "pip", "freeze"],
        cwd=cwd,
        env=env,
        log_output=False,  # Don't log the full freeze output
    )
    deduplicated_output = _deduplicate_freeze_requirements(freeze_result.stdout)
    requirements_in = Path(cwd) / "flow-requirements.in"
    with open(requirements_in, "w") as f:
        f.write(deduplicated_output)

    try:
        compile_result = run_with_logging(
            [
                "uv",
                "pip",
                "compile",
                "--generate-hashes",
                "--no-header",
                "--no-annotate",
                "--no-deps",
                str(requirements_in),
            ],
            cwd=cwd,
            env=env,
            log_output=False,
        )
        fs = filesystem(spec.log_dir)
        fs.mkdir(spec.log_dir, exist_ok=True)
        with file(spec.log_dir + "/flow-requirements.txt", "w") as f:
            f.write(compile_result.stdout)
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.output or "").strip()
        msg = f"Failed to generate flow-requirements.txt: {e}"
        if detail:
            msg += f"\n{detail}"
        logger.warning(msg)
    finally:
        requirements_in.unlink()


def _deduplicate_freeze_requirements(freeze_output: str) -> str:
    """Deduplicate package entries in freeze output, keeping the most specific URL."""
    lines = freeze_output.strip().split("\n")
    packages: dict[str, str] = {}

    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue

        # Extract package name (handle both regular and URL-based packages)
        # Format: "package==version" or "package @ url"
        package_name = line.split("==")[0].split(" @ ")[0].strip()

        if package_name not in packages:
            packages[package_name] = line
        else:
            existing = packages[package_name]
            # Check if either line has a git URL with commit hash (@<hash>)
            # Prefer: git+...@<commit_hash> over git+...@<branch> over git+...
            if " @ git+" in line and " @ git+" in existing:
                # Both are git URLs, prefer the one with what looks like a commit hash
                # Commit hashes are typically 40 chars, branches are shorter
                line_ref = (
                    line.split("@")[-1] if "@" in line.split(" @ git+")[-1] else ""
                )
                existing_ref = (
                    existing.split("@")[-1]
                    if "@" in existing.split(" @ git+")[-1]
                    else ""
                )

                if len(line_ref) > len(existing_ref):
                    packages[package_name] = line
            elif " @ git+" in line:
                # New line is git URL, existing is not - prefer git URL
                packages[package_name] = line

    return "\n".join(packages.values()) + "\n"
