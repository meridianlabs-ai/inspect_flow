"""The dependency cooldown in pyproject.toml and the CI jobs that install from uv.lock.

pyproject.toml holds back releases younger than seven days, or six hours for a
list of model provider SDKs and Inspect packages. Dependabot applies the seven
days to its uv.lock bumps and leaves that list to uv. Every Python job in
build.yaml installs from uv.lock through the shared install action. The
publish jobs build with uv build after the shared setup-uv.
"""

import re
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).parents[1]
GITHUB = REPO / ".github"
BUILD = GITHUB / "workflows" / "build.yaml"
INSTALL_ACTION = "meridianlabs-ai/actions/install-python-dependencies@"
SETUP_UV = "meridianlabs-ai/actions/setup-uv@"
MATRIX_PYTHON = "${{ matrix.python-version }}"
DEV = {"versions": "locked", "python-version": MATRIX_PYTHON, "extras": "dev"}
LOCKED_JOBS = {
    "py-ruff": DEV,
    "py-type": DEV,
    "py-test": DEV,
    "check-type-gen": DEV,
    "py-build": {
        "versions": "locked",
        "python-version": MATRIX_PYTHON,
        "project-install": "skip",
        "default-dependency-groups": "exclude",
    },
}
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


def dependabot_uv() -> dict[str, Any]:
    updates = yaml.safe_load((GITHUB / "dependabot.yml").read_text())["updates"]
    (root,) = [
        u for u in updates if u["package-ecosystem"] == "uv" and u["directory"] == "/"
    ]
    return root


def build_jobs() -> dict[str, Any]:
    jobs: dict[str, Any] = yaml.safe_load(BUILD.read_text())["jobs"]
    return jobs


def run_lines(job: dict[str, Any]) -> list[str]:
    return [
        line.strip()
        for step in job["steps"]
        for line in step.get("run", "").replace("\\\n", " ").splitlines()
        if line.strip()
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
    python_jobs = {
        name
        for name, job in build_jobs().items()
        if any(re.search(r"\b(uv|pip|python)\b", line) for line in run_lines(job))
    }
    assert python_jobs <= set(LOCKED_JOBS)


@pytest.mark.parametrize("name,inputs", LOCKED_JOBS.items())
def test_python_jobs_install_from_the_lockfile(
    name: str, inputs: dict[str, str]
) -> None:
    job = build_jobs()[name]
    installs = [
        step.get("with")
        for step in job["steps"]
        if step.get("uses", "").startswith(INSTALL_ACTION)
    ]
    assert installs == [inputs]
    # A bare `uv run` or `uv sync` re-locks, `--with` and pip installs skip
    # uv.lock, and `--exclude-newer` overrides the cooldown.
    unlocked = [
        line
        for line in run_lines(job)
        if re.search(r"\buv sync\b|--with\b|--exclude-newer\b", line)
        or (re.search(r"\buv run\b", line) and "--no-sync" not in line.split())
        or (
            re.search(r"\bpip3? install\b", line)
            and not line.startswith("uv pip install --no-deps ")
        )
    ]
    assert unlocked == []


@pytest.mark.parametrize("workflow", ["publish.yaml", "release.yaml"])
def test_publish_uses_the_shared_setup_uv(workflow: str) -> None:
    job = yaml.safe_load((GITHUB / "workflows" / workflow).read_text())["jobs"][
        "publish"
    ]
    uses = [step["uses"] for step in job["steps"] if "uses" in step]
    setups = [
        step.get("with")
        for step in job["steps"]
        if step.get("uses", "").startswith(SETUP_UV)
    ]
    # The job holds id-token: write, so it restores no Actions cache.
    assert setups == [{"python-version": "3.14", "actions-cache": "none"}]
    assert not [
        u
        for u in uses
        if u.startswith(
            ("actions/setup-python@", "astral-sh/setup-uv@", "actions/cache@")
        )
    ]
    assert not [
        line for line in run_lines(job) if re.search(r"\bpip3? install\b", line)
    ]
