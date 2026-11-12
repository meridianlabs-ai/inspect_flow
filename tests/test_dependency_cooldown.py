"""The dependency cooldown in pyproject.toml and the CI jobs that install from uv.lock.

pyproject.toml holds back releases younger than seven days, or six hours for a
list of model provider SDKs and Inspect packages. Dependabot applies the seven
days to its uv.lock bumps and leaves that list to uv. Every Python job in
build.yaml installs from uv.lock through the shared install action. py-build
builds with the toolchain pinned with hashes in
scripts/build-dist/requirements.txt, also through the shared action. The
release workflow builds with the same file in the shared build workflow, and
its publish job only uploads that build. Venv mode applies the same cooldown
by default to the environments it creates.
"""

import re
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from inspect_flow._launcher.uv_settings import (
    DEFAULT_COOLDOWN,
    SHORT_COOLDOWN,
    SHORT_COOLDOWN_PACKAGES,
)

REPO = Path(__file__).parents[1]
GITHUB = REPO / ".github"
WORKFLOWS = GITHUB / "workflows"
BUILD = WORKFLOWS / "build.yaml"
RELEASE = "release.yaml"
INSTALL_ACTION = "meridianlabs-ai/actions/install-python-dependencies@"
SHARED_BUILD = "meridianlabs-ai/actions/.github/workflows/build-python-dist.yml@"
PUBLISH_STEPS = ("actions/download-artifact@", "pypa/gh-action-pypi-publish@")
DOWNLOAD_INPUTS = {
    "artifact-ids": "${{ needs.build.outputs.artifact-id }}",
    "path": "dist/",
}
MATRIX_PYTHON = "${{ matrix.python-version }}"
TOOLCHAIN = {
    "versions": "hashed-requirements",
    "requirements-file": "scripts/build-dist/requirements.txt",
    "package-format": "wheels-only",
    "environment-dir": "${{ runner.temp }}/build-venv",
}
DEV = {"versions": "locked", "python-version": MATRIX_PYTHON, "extras": "dev"}
LOCKED_JOBS = {
    "py-ruff": [DEV],
    "py-type": [DEV],
    "py-test": [DEV],
    "check-type-gen": [DEV],
    "py-build": [
        {**TOOLCHAIN, "python-version": MATRIX_PYTHON},
        {
            "versions": "locked",
            "python-version": MATRIX_PYTHON,
            "project-install": "skip",
            "default-dependency-groups": "exclude",
            "also-install-without-deps": "${{ steps.build.outputs.wheel }}",
        },
    ],
}
BUILD_NO_ISOLATION = '"$RUNNER_TEMP/build-venv/bin/python" -m build --no-isolation'
SIX_HOURS = "6 hours"


def pyproject() -> dict[str, Any]:
    return tomllib.loads((REPO / "pyproject.toml").read_text())


def normalize(package: str) -> str:
    return re.sub(r"[-_.]+", "-", package).lower()


def six_hour_packages() -> list[str]:
    packages = pyproject()["tool"]["uv"]["exclude-newer-package"]
    return sorted(
        normalize(p) for p, cooldown in packages.items() if cooldown == SIX_HOURS
    )


def dependabot_uv(directory: str = "/") -> dict[str, Any]:
    updates = yaml.safe_load((GITHUB / "dependabot.yml").read_text())["updates"]
    (update,) = [
        u
        for u in updates
        if u["package-ecosystem"] == "uv" and u["directory"] == directory
    ]
    return update


def build_jobs() -> dict[str, Any]:
    jobs: dict[str, Any] = yaml.safe_load(BUILD.read_text())["jobs"]
    return jobs


def workflow_jobs(workflow: str) -> dict[str, Any]:
    jobs: dict[str, Any] = yaml.safe_load((WORKFLOWS / workflow).read_text())["jobs"]
    return jobs


def needs(job: dict[str, Any]) -> list[str]:
    value: str | list[str] = job.get("needs", [])
    return [value] if isinstance(value, str) else value


def run_lines(job: dict[str, Any]) -> list[str]:
    return [
        line.strip()
        for step in job.get("steps", [])
        for line in step.get("run", "").replace("\\\n", " ").splitlines()
        if line.strip()
    ]


def install_and_build_steps(job: dict[str, Any]) -> list[str]:
    return [
        "install" if step.get("uses", "").startswith(INSTALL_ACTION) else "build"
        for step in job["steps"]
        if step.get("uses", "").startswith(INSTALL_ACTION)
        or BUILD_NO_ISOLATION in step.get("run", "").splitlines()
    ]


def test_exclude_newer_package_entries() -> None:
    uv = pyproject()["tool"]["uv"]
    assert uv["exclude-newer"] == "7 days"
    project = pyproject()["project"]
    direct = {
        normalize(re.split(r"[^A-Za-z0-9._-]", requirement, maxsplit=1)[0])
        for requirement in project["dependencies"]
        + project["optional-dependencies"]["dev"]
    }
    now = datetime.now(UTC)
    for package, cooldown in uv["exclude-newer-package"].items():
        assert normalize(package) in direct, package
        # Otherwise a dated emergency entry, removed before the cooldown passes it.
        if cooldown != SIX_HOURS:
            assert isinstance(cooldown, str), f"{package} = {cooldown!r}"
            age = now - datetime.fromisoformat(cooldown).astimezone(UTC)
            assert timedelta(0) <= age < timedelta(days=7), f"{package} = {cooldown}"


def test_dependabot_cooldown_matches_pyproject() -> None:
    dependabot = dependabot_uv()
    assert dependabot["cooldown"]["default-days"] == 7
    # inspect-update.yml bumps inspect-ai.
    assert dependabot["ignore"] == [{"dependency-name": "inspect-ai"}]
    # Dependabot's cooldown counts whole days, so it leaves the 6-hour packages to uv.
    exempt = [p for p in six_hour_packages() if p != "inspect-ai"]
    assert sorted(dependabot["cooldown"]["exclude"]) == exempt
    groups = dependabot["groups"]
    assert list(groups) == ["six-hour-cooldown", "python-packages"]
    assert sorted(groups["six-hour-cooldown"]["patterns"]) == exempt
    assert groups["python-packages"]["patterns"] == ["*"]


def test_venv_default_cooldown_matches_pyproject() -> None:
    days = int(pyproject()["tool"]["uv"]["exclude-newer"].removesuffix(" days"))
    assert DEFAULT_COOLDOWN == timedelta(days=days)
    assert SHORT_COOLDOWN == timedelta(hours=int(SIX_HOURS.removesuffix(" hours")))
    assert sorted(SHORT_COOLDOWN_PACKAGES) == six_hour_packages()


def test_dependabot_build_toolchain_cooldown_matches_pyproject() -> None:
    days = int(pyproject()["tool"]["uv"]["exclude-newer"].removesuffix(" days"))
    assert dependabot_uv("/scripts/build-dist")["cooldown"]["default-days"] == days


def test_build_installs_only_through_the_shared_action() -> None:
    uses = [
        step["uses"]
        for job in build_jobs().values()
        for step in job["steps"]
        if "uses" in step
    ]
    assert not [
        u
        for u in uses
        if u.startswith(("astral-sh/setup-uv@", "actions/setup-python@"))
    ]
    refs = {
        u.removeprefix(INSTALL_ACTION) for u in uses if u.startswith(INSTALL_ACTION)
    }
    assert len(refs) == 1, refs
    assert re.fullmatch(r"[0-9a-f]{40}", refs.pop())


def test_every_python_job_is_locked() -> None:
    python = r"\b(uvx?|pip3?|python3?)\b"
    python_jobs = {
        name
        for name, job in build_jobs().items()
        if any(re.search(python, line) for line in run_lines(job))
        or any(re.search(python, step.get("shell", "")) for step in job["steps"])
    }
    assert python_jobs <= set(LOCKED_JOBS)


@pytest.mark.parametrize("name,inputs", LOCKED_JOBS.items())
def test_python_jobs_install_from_the_lockfile(
    name: str, inputs: list[dict[str, str]]
) -> None:
    job = build_jobs()[name]
    installs = [
        step.get("with")
        for step in job["steps"]
        if step.get("uses", "").startswith(INSTALL_ACTION)
    ]
    assert installs == inputs
    # A bare `uv run` or `uv sync` re-locks, `--with` and pip installs skip
    # uv.lock, and `--exclude-newer` overrides the cooldown.
    unlocked = [
        line
        for line in run_lines(job)
        if re.search(r"\buv sync\b|--with\b|--exclude-newer\b", line)
        or (re.search(r"\buv run\b", line) and "--no-sync" not in line.split())
        or re.search(r"\bpip3? install\b", line)
    ]
    assert unlocked == []


def test_py_build_builds_between_toolchain_and_locked_install() -> None:
    steps = install_and_build_steps(build_jobs()["py-build"])
    assert steps == ["install", "build", "install"]


def test_publish_builds_in_the_shared_workflow() -> None:
    build = workflow_jobs(RELEASE)["build"]
    assert build["uses"].startswith(SHARED_BUILD), build["uses"]
    ref = build["uses"].removeprefix(SHARED_BUILD).split()[0]
    assert re.fullmatch(r"[0-9a-f]{40}", ref), "pin a 40-character SHA"
    assert build["with"] == {"python-version": "3.11"}
    assert build["permissions"] == {"contents": "read"}


def test_publish_jobs_only_upload_the_shared_build() -> None:
    jobs = workflow_jobs(RELEASE)
    publishers = [
        job
        for job in jobs.values()
        if job.get("permissions", {}).get("id-token") == "write"
    ]
    assert publishers, "no job holds id-token: write"
    for job in publishers:
        steps = [step.get("uses", "") for step in job["steps"]]
        assert len(steps) == len(PUBLISH_STEPS)
        assert all(map(str.startswith, steps, PUBLISH_STEPS)), steps
        assert "build" in needs(job)
        assert job["steps"][0]["with"] == DOWNLOAD_INPUTS
    # Without the release-please tag, hatch-vcs builds a dev version.
    build = jobs["build"]
    assert "release-please" in needs(build)
    assert all(build["if"] == job["if"] for job in publishers)


@pytest.mark.parametrize("workflow", ["build.yaml", RELEASE])
def test_no_build_or_install_outside_the_shared_action(workflow: str) -> None:
    jobs = yaml.safe_load((WORKFLOWS / workflow).read_text())["jobs"]
    assert not [
        line
        for job in jobs.values()
        for line in run_lines(job)
        if re.search(r"\buv (build|pip install)\b", line)
    ]
