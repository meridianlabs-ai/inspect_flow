"""Tests for the shell steps of .github/workflows/inspect-update.yml.

The `agent` job's "Surface agent errors" and "Compose landing manifest" steps
are run with bash against a fixture execution file shaped like the result
record claude-code-action writes (a `permission_denials` list of
`{tool_name, tool_use_id, tool_input}`), so a refused commit is reported on
the release issue instead of passing as a silent success (run 35446410455).

The `gate` job's "Dedup before doing any work" step is run against a stub `gh`
(tests/fixtures/gh_stub/gh) that serves canned list-endpoint pages: the gate
must decide from `repos/*/pulls` and `repos/*/issues`, never from the search
API, whose results under the job token differ from a user's (runs 35611948106
and 35614947712 refused on an open labelled issue counted as a pull request).

The PR labels each composer writes (here and in inspect-ai-main-failure.yml)
must be exactly the `allowed-pr-labels` its `land` step pins, so a manifest
rewritten after the composer cannot add another label (#847).

Every job that runs the agent restores the Actions cache but never saves it
(meridianlabs-ai/agents design/agent-cache-scope.md).

The `land` job's "Route protected changes to the maintainer" step is run
against a local origin and a bundle built like emit-landing's: commits that
change a protected path (run 35921391185: pyproject.toml and uv.lock, which
the shared land action refuses to push) become a maintainer handoff whose
kept bundle applies from the handoff comment's own commands onto the draft
PR's branch, while other commits are left to land as before. The "Open the
maintainer's draft PR" step pushes that branch with a placeholder note and none
of the agent's objects, and a re-run adopts the branch and PR it made.

Both scheduled agent workflows have land open their PRs as drafts assigned to
ransomr (agents#175's `pr-draft` and `pr-assignees`), and neither carries the
`auto` label (#859 sat labelled `auto`, never reviewed).

Every call of the agents repo's reusable workflows sets the `provision` recipe
the agent user runs in place of claude-setup, with claude-setup's Python
(meridianlabs-ai/agents design/executed-paths-residual.md).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).parent.parent / ".github/workflows"
WORKFLOW = WORKFLOWS / "inspect-update.yml"
GH_STUB = Path(__file__).parent / "fixtures/gh_stub"

HEREDOC_COMMIT = "git commit -m \"$(cat <<'EOF'\nfix: upgrade lock\nEOF\n)\""

DENIED_RESULT = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "num_turns": 97,
    "result": "Upgraded the lock and implemented the review surface in the PR.",
    "permission_denials": [
        {
            "tool_name": "Bash",
            "tool_use_id": "toolu_01",
            "tool_input": {"command": HEREDOC_COMMIT, "description": "Commit"},
        },
        {
            "tool_name": "Edit",
            "tool_use_id": "toolu_02",
            "tool_input": {"file_path": "/etc/hosts", "old_string": "a\nb"},
        },
    ],
}

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("bash") is None,
    reason="the workflow steps need bash and jq",
)


def _steps(job: str, path: Path = WORKFLOW) -> dict[str, dict[str, Any]]:
    workflow = yaml.safe_load(path.read_text())
    return {
        step["name"]: step for step in workflow["jobs"][job]["steps"] if "name" in step
    }


def _prompt() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    step = next(
        s for s in workflow["jobs"]["agent"]["steps"] if s.get("id") == "claude"
    )
    return step["with"]["prompt"]


def _run_step(name: str, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        ["bash", "-c", _steps("agent")[name]["run"]],
        cwd=cwd,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", **env},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _commit(repo, "start")
    return repo


def _env(tmp_path: Path, repo: Path, result: dict[str, Any]) -> dict[str, str]:
    exec_file = tmp_path / "claude-execution-output.json"
    exec_file.write_text(json.dumps([{"type": "system", "subtype": "init"}, result]))
    out = tmp_path / "agent-out"
    out.mkdir()
    (out / "issue-comment.md").write_text("## Mapping\n\nAll done.\n")
    return {
        "EXEC": str(exec_file),
        "CLAUDE_OUTCOME": "success",
        "START": _git(repo, "rev-parse", "HEAD"),
        "ERROR_FILE": str(tmp_path / "agent-error.md"),
        "WARN_FILE": str(tmp_path / "agent-warning.md"),
        "DIR": str(tmp_path / "landing"),
        "OUT": str(out),
        "EXTRA": str(tmp_path / "landing-extra.json"),
        "LATEST": "0.3.266",
        "ISSUE": "836",
        "PROV_NOTE": "",
    }


def _commit(repo: Path, message: str = "work") -> None:
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        message,
    )


def test_denials_without_commits_fail_the_run(tmp_path: Path, repo: Path) -> None:
    env = _env(tmp_path, repo, DENIED_RESULT)
    log = _run_step("Surface agent errors", repo, env)
    _run_step("Compose landing manifest", repo, env)

    assert "::error::No commit landed and 2 tool call(s) were refused" in log
    assert not Path(env["WARN_FILE"]).exists()
    extra = json.loads(Path(env["EXTRA"]).read_text())
    message = extra["error"]["message"]
    assert extra["error"]["fail_run"] is True
    assert "2 tool call(s) were refused by the permission allow-list" in message
    # Each refused input on one line, the Bash command verbatim.
    assert (
        "    Bash: git commit -m \"$(cat <<'EOF' fix: upgrade lock EOF )\"" in message
    )
    assert '    Edit: {"file_path":"/etc/hosts"' in message
    assert message.rstrip().endswith(
        "The agent made no commits, so no branch was pushed and no PR was opened."
    )
    assert "pr" not in extra
    assert extra["comments"] == [{"number": 836, "body_file": "issue-comment.md"}]


def test_denials_with_commits_only_warn(tmp_path: Path, repo: Path) -> None:
    env = _env(tmp_path, repo, DENIED_RESULT)
    _commit(repo)
    log = _run_step("Surface agent errors", repo, env)
    _run_step("Compose landing manifest", repo, env)

    assert "::warning::2 tool call(s) were refused" in log
    assert not Path(env["ERROR_FILE"]).exists()
    extra = json.loads(Path(env["EXTRA"]).read_text())
    assert "error" not in extra
    assert extra["pr"]["open"] is True
    comment = (Path(env["DIR"]) / "issue-comment.md").read_text()
    assert comment.startswith("⚠️ 2 tool call(s) were refused")
    assert "    Bash: git commit -m" in comment
    assert comment.endswith("\n\n## Mapping\n\nAll done.\n")


def _denied_commands(command: str) -> dict[str, Any]:
    denials = [
        {
            "tool_name": "Bash",
            "tool_use_id": f"toolu_{i}",
            "tool_input": {"command": command},
        }
        for i in range(10)
    ]
    return {**DENIED_RESULT, "permission_denials": denials}


@pytest.mark.parametrize("command", ["x" * 300, "界" * 300])
def test_denial_warning_fits_the_posting_budget_before_a_full_mapping(
    tmp_path: Path, repo: Path, command: str
) -> None:
    """land posts at most 60,000 bytes of a comment, so a warning appended after a
    full-size mapping would be cut off (or, with multibyte inputs, the file would
    exceed the manifest's 64 KiB cap and nothing would land)."""
    env = _env(tmp_path, repo, _denied_commands(command))
    (Path(env["OUT"]) / "issue-comment.md").write_bytes(b"# Mapping\n" + b"m" * 60000)
    _commit(repo)
    _run_step("Surface agent errors", repo, env)
    _run_step("Compose landing manifest", repo, env)

    extra = json.loads(Path(env["EXTRA"]).read_text())
    assert "error" not in extra
    assert extra["comments"] == [{"number": 836, "body_file": "issue-comment.md"}]
    comment = (Path(env["DIR"]) / "issue-comment.md").read_bytes()
    assert len(comment) <= 60000
    text = comment.decode()
    assert text.startswith("⚠️ 10 tool call(s) were refused")
    assert text.count(f"    Bash: {command[:200]}\n") == 10
    assert "\n\n# Mapping\nmmm" in text


def test_denials_warning_posts_without_agent_comment(
    tmp_path: Path, repo: Path
) -> None:
    env = _env(tmp_path, repo, DENIED_RESULT)
    (Path(env["OUT"]) / "issue-comment.md").unlink()
    _commit(repo)
    _run_step("Surface agent errors", repo, env)
    _run_step("Compose landing manifest", repo, env)

    extra = json.loads(Path(env["EXTRA"]).read_text())
    assert "left no changelog mapping" in extra["error"]["message"]
    assert extra["comments"] == [{"number": 836, "body_file": "issue-comment.md"}]
    comment = (Path(env["DIR"]) / "issue-comment.md").read_text()
    assert comment.startswith("⚠️ 2 tool call(s) were refused")


def test_no_denials_and_no_error_is_clean(tmp_path: Path, repo: Path) -> None:
    result = {**DENIED_RESULT, "permission_denials": []}
    env = _env(tmp_path, repo, result)
    _commit(repo)
    log = _run_step("Surface agent errors", repo, env)
    _run_step("Compose landing manifest", repo, env)

    assert log.strip() == "No agent error detected."
    assert not Path(env["ERROR_FILE"]).exists()
    assert not Path(env["WARN_FILE"]).exists()
    assert "error" not in json.loads(Path(env["EXTRA"]).read_text())


def test_api_error_result_is_still_reported(tmp_path: Path, repo: Path) -> None:
    result = {
        "type": "result",
        "subtype": "error_during_execution",
        "is_error": True,
        "result": "API Error: 529 overloaded",
    }
    env = _env(tmp_path, repo, result)
    log = _run_step("Surface agent errors", repo, env)
    _run_step("Compose landing manifest", repo, env)

    assert "::error::Claude run did not complete: API Error: 529 overloaded" in log
    message = json.loads(Path(env["EXTRA"]).read_text())["error"]["message"]
    assert "> API Error: 529 overloaded" in message
    assert "refused" not in message


def test_prompt_says_how_to_commit() -> None:
    prompt = _prompt()
    assert "`git add -A` (or `git add <paths>`) as one" in prompt
    assert '`git commit -m "<one-line message>"` as a' in prompt
    assert "No heredoc message, no `$(...)`, no" in prompt
    assert "if the same command is refused twice, stop retrying" in prompt
    assert "OUT/pr-title.txt and OUT/pr-body.md (step 5) BEFORE your first" in prompt


GATE_STEP = "Dedup before doing any work"


def _pr(number: int, *labels: str) -> dict[str, Any]:
    return {"number": number, "labels": [{"name": name} for name in labels]}


def _issue(number: int, title: str, pr: bool = False) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "number": number,
        "title": title,
        "labels": [{"name": "inspect-update"}],
    }
    if pr:
        entry["pull_request"] = {"url": f"https://api.github.com/pulls/{number}"}
    return entry


def _run_gate(
    tmp_path: Path,
    pulls: list[list[dict[str, Any]]],
    issues: list[list[dict[str, Any]]],
    latest: str = "0.3.266",
    reconciled: str = "0.3.265",
    fail: bool = False,
    handoffs: list[dict[str, Any]] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], list[str]]:
    """Run the gate's dedup step against the stub gh; return the process, the
    step outputs and the gh calls it made. `--paginate` prints one array per
    page, so multi-page fixtures are concatenated documents."""
    pulls_file = tmp_path / "pulls.json"
    issues_file = tmp_path / "issues.json"
    pulls_file.write_text("\n".join(json.dumps(page) for page in pulls))
    issues_file.write_text("\n".join(json.dumps(page) for page in issues))
    handoffs_file = tmp_path / "handoffs.json"
    handoffs_file.write_text(json.dumps(handoffs or []))
    output = tmp_path / "github-output"
    output.touch()
    log = tmp_path / "gh-calls.log"
    env = {
        "PATH": f"{GH_STUB}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "GITHUB_OUTPUT": str(output),
        "GITHUB_REPOSITORY": "meridianlabs-ai/inspect_flow",
        "LATEST": latest,
        "RECONCILED": reconciled,
        "GH_STUB_LOG": str(log),
        "GH_STUB_PULLS": str(pulls_file),
        "GH_STUB_ISSUES": str(issues_file),
        "GH_STUB_HANDOFFS": str(handoffs_file),
        **({"GH_STUB_FAIL": "1"} if fail else {}),
    }
    result = subprocess.run(
        ["bash", "-c", _steps("gate")[GATE_STEP]["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    outputs = dict(
        line.split("=", 1) for line in output.read_text().splitlines() if line
    )
    calls = log.read_text().splitlines() if log.exists() else []
    return result, outputs, calls


def test_gate_decides_from_the_list_endpoints_not_search() -> None:
    run = _steps("gate")[GATE_STEP]["run"]
    assert "search/issues" not in run
    assert "pulls?state=open" in run
    assert "issues?state=all&labels=inspect-update" in run
    # The version is matched as a whole token, dots taken literally.
    assert "(^|[^0-9.])" in run and "([^0-9.]|$)" in run
    assert 'gsub("\\\\."; "\\\\.")' in run


def test_gate_proceeds_past_an_open_labelled_issue(tmp_path: Path) -> None:
    """The failure of 2026-09-21: an open `inspect-update` issue for an earlier
    attempt (no version in its title) and an unrelated open PR must not read
    as a PR still in flight or as the release already claimed."""
    result, outputs, calls = _run_gate(
        tmp_path,
        pulls=[[_pr(840, "auto")]],
        issues=[
            [
                _issue(836, "Superseded reconciliation attempt of 2026-09-19"),
                _issue(
                    812, "inspect-ai 0.3.265: surface new features in flow", pr=True
                ),
            ]
        ],
    )

    assert result.returncode == 0, result.stderr
    assert outputs == {"proceed": "true"}
    assert "inspect-ai 0.3.266 is unprocessed; proceeding." in result.stdout
    assert [c.split()[1] for c in calls] == [
        "repos/meridianlabs-ai/inspect_flow/pulls?state=open&per_page=100",
        "repos/meridianlabs-ai/inspect_flow/issues?state=open&labels=inspect-update,maintainer-handoff&per_page=100",
        "repos/meridianlabs-ai/inspect_flow/issues?state=all&labels=inspect-update&per_page=100",
    ]
    assert all("--paginate" in c and "search" not in c for c in calls)


def test_gate_waits_for_an_open_inspect_update_pr(tmp_path: Path) -> None:
    result, outputs, calls = _run_gate(
        tmp_path,
        pulls=[[_pr(840, "auto")], [_pr(842, "auto", "inspect-update")]],
        issues=[[]],
    )

    assert result.returncode == 0, result.stderr
    assert outputs == {"proceed": "false"}
    assert "An inspect-update PR is still open; waiting" in result.stdout
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("title", "proceed"),
    [
        ("inspect-ai 0.3.266: surface new features in flow", "false"),
        ("chore: reconcile inspect-ai 0.3.266", "false"),
        ("0.3.266", "false"),
        ("inspect-ai 0.3.2660: surface new features in flow", "true"),
        ("inspect-ai 10.3.266: surface new features in flow", "true"),
        ("inspect-ai 0.3.266.1: surface new features in flow", "true"),
        ("inspect-ai 0x3x266: surface new features in flow", "true"),
    ],
)
def test_gate_matches_the_claimed_version_as_a_whole_token(
    tmp_path: Path, title: str, proceed: str
) -> None:
    result, outputs, _ = _run_gate(
        tmp_path,
        pulls=[[]],
        issues=[
            [_issue(700, "inspect-ai 0.3.200: older")],
            [_issue(843, title, pr=True)],
        ],
    )

    assert result.returncode == 0, result.stderr
    assert outputs == {"proceed": proceed}
    if proceed == "false":
        assert (
            "Found 1 existing inspect-update issue(s)/PR(s) for 0.3.266"
            in result.stdout
        )


def test_gate_waits_for_an_open_maintainer_handoff(tmp_path: Path) -> None:
    """A release handed to the maintainer has not advanced the marker on main,
    so a newer release would reconcile a superset of it: wait for the
    maintainer's PR to close the handoff issue (a PR carrying both labels is
    the open-PR rule's, not this one's)."""
    result, outputs, calls = _run_gate(
        tmp_path,
        pulls=[[]],
        issues=[[]],
        latest="0.3.269",
        reconciled="0.3.266",
        handoffs=[_issue(852, "inspect-ai 0.3.268: surface new features in flow")],
    )

    assert result.returncode == 0, result.stderr
    assert outputs == {"proceed": "false"}
    assert "maintainer handoff is still open; waiting" in result.stdout
    assert len(calls) == 2

    (tmp_path / "pr").mkdir()
    result, outputs, _ = _run_gate(
        tmp_path / "pr",
        pulls=[[]],
        issues=[[]],
        latest="0.3.269",
        reconciled="0.3.266",
        handoffs=[_issue(853, "chore: reconcile inspect-ai 0.3.268", pr=True)],
    )
    assert outputs == {"proceed": "true"}


def test_gate_fails_loudly_when_gh_fails(tmp_path: Path) -> None:
    result, outputs, _ = _run_gate(tmp_path, pulls=[[]], issues=[[]], fail=True)

    assert result.returncode != 0
    assert "HTTP 502" in result.stderr
    assert outputs == {}


def test_gate_skips_gh_when_already_reconciled(tmp_path: Path) -> None:
    result, outputs, calls = _run_gate(
        tmp_path, pulls=[[]], issues=[[]], latest="0.3.266", reconciled="0.3.266"
    )

    assert result.returncode == 0, result.stderr
    assert outputs == {"proceed": "false"}
    assert calls == []


@pytest.mark.parametrize(
    ("workflow", "agent_job", "land_job"),
    [
        ("inspect-update.yml", "agent", "land"),
        ("inspect-ai-main-failure.yml", "triage-agent", "triage-land"),
    ],
)
def test_land_allows_only_the_labels_the_composer_writes(
    tmp_path: Path, repo: Path, workflow: str, agent_job: str, land_job: str
) -> None:
    compose = _steps(agent_job, WORKFLOWS / workflow)["Compose landing manifest"]
    land = _steps(land_job, WORKFLOWS / workflow)["Land"]
    env = _env(tmp_path, repo, {"type": "result", "subtype": "success"})
    _commit(repo)
    output = tmp_path / "github-output"
    output.touch()
    subprocess.run(
        ["bash", "-c", compose["run"]],
        cwd=repo,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "GITHUB_OUTPUT": str(output),
            **env,
        },
        capture_output=True,
        check=True,
    )
    labels = json.loads(Path(env["EXTRA"]).read_text())["pr"]["labels"]
    assert json.loads(land["with"]["allowed-pr-labels"]) == labels


def test_agent_jobs_only_read_the_actions_cache() -> None:
    agent_jobs = {
        (path.name, name): job.get("cache-mode")
        for path in WORKFLOWS.glob("*.yml")
        for name, job in yaml.safe_load(path.read_text())["jobs"].items()
        if job.get("uses", "").startswith("meridianlabs-ai/agents/.github/workflows/")
        or any(
            step.get("uses", "").startswith("anthropics/claude-code-action")
            for step in job.get("steps", [])
        )
    }
    assert agent_jobs == {
        ("inspect-update.yml", "agent"): "read",
        ("inspect-ai-main-failure.yml", "triage-agent"): "read",
        ("claude.yml", "claude"): "read",
        ("claude.yml", "claude-auto"): "read",
        ("claude-auto.yml", "ci-fix"): "read",
        ("claude-auto.yml", "review-fix"): "read",
        ("claude-review.yml", "review"): "read",
    }


def test_agent_stubs_provision_like_claude_setup() -> None:
    claude_setup = yaml.safe_load(
        (WORKFLOWS.parent / "actions/claude-setup/action.yaml").read_text()
    )
    python = claude_setup["runs"]["steps"][0]["with"]["python-version"]
    recipe = f"uv venv --python {python}\nuv sync --dev\n"
    stub_calls = {
        (path.name, name): job.get("with", {}).get("provision")
        for path in WORKFLOWS.glob("*.yml")
        for name, job in yaml.safe_load(path.read_text())["jobs"].items()
        if job.get("uses", "").startswith("meridianlabs-ai/agents/.github/workflows/")
    }
    assert stub_calls == {
        ("claude.yml", "claude"): recipe,
        ("claude.yml", "claude-auto"): recipe,
        ("claude-auto.yml", "ci-fix"): recipe,
        ("claude-auto.yml", "review-fix"): recipe,
        ("claude-review.yml", "review"): recipe,
    }


ROUTE_STEP = "Route protected changes to the maintainer"
LAND_ACTIONS = "_actions/meridianlabs-ai/agents/main/.github/actions/land"

# Stands in for the land action's lib.sh: the same two names the route step
# reads, with a protected list shaped like the real one.
STUB_LIB = """PROTECTED_PATHSPECS=(.github ':(glob)**/pyproject.toml' ':(glob)**/uv.lock')
protected_reach() { :; }
"""


def _land_steps() -> dict[str, dict[str, Any]]:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    return {s["id"]: s for s in workflow["jobs"]["land"]["steps"] if "id" in s}


def _write(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    _git(repo, "add", "-A")
    _commit(repo, "agent work")


class Landing:
    """A local origin at `start`, an agent clone with commits above it, and the
    landing directory emit-landing and the composer would upload for them."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.origin = tmp_path / "origin"
        self.origin.mkdir()
        _git(self.origin, "init", "-q", "-b", "main")
        _write(
            self.origin, {"pyproject.toml": "[tool.inspect_flow]\n", "uv.lock": "a\n"}
        )
        self.start = _git(self.origin, "rev-parse", "HEAD")
        self.agent = tmp_path / "agent"
        _git(tmp_path, "clone", "-q", str(self.origin), str(self.agent))
        self.src = tmp_path / "runner/temp/route/src"
        self.route = tmp_path / "runner/temp/route"
        self.workspace = tmp_path / "runner/work/inspect_flow"
        self.workspace.mkdir(parents=True)
        lib = tmp_path / "runner/work" / LAND_ACTIONS / "lib.sh"
        lib.parent.mkdir(parents=True)
        lib.write_text(STUB_LIB)
        self.lib = lib
        self.output = tmp_path / "github-output"

    def emit(self, start: str | None = None, head: str | None = None) -> None:
        self.src.mkdir(parents=True)
        tip = _git(self.agent, "rev-parse", "HEAD")
        has_bundle = tip != self.start
        if has_bundle:
            _git(
                self.agent,
                "bundle",
                "create",
                "-q",
                str(self.src / "commits.bundle"),
                f"{self.start}..HEAD",
            )
        (self.src / "pr-body.md").write_text("Fixes #852\n\nAgent PR body.\n")
        (self.src / "issue-comment.md").write_text("## Mapping\n")
        manifest = {
            "comments": [{"number": 852, "body_file": "issue-comment.md"}],
            "schema": 1,
            "repo": "meridianlabs-ai/inspect_flow",
            "run_id": 35921391185,
            "branch": "inspect-update/852/0.3.268",
            "start_sha": start or self.start,
            "head_sha": head or tip,
            "has_bundle": has_bundle,
            "pr_number": None,
            "issue_number": 852,
        }
        if has_bundle:
            manifest["pr"] = {
                "open": True,
                "title": "chore: reconcile inspect-ai 0.3.268",
                "body_file": "pr-body.md",
                "labels": ["inspect-update"],
                "issue": 852,
            }
        (self.src / "manifest.json").write_text(json.dumps(manifest))

    def run(
        self, attempt: int = 1
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
        self.output.write_text("")
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(self.tmp),
            "GITHUB_OUTPUT": str(self.output),
            "RUNNER_WORKSPACE": str(self.workspace),
            "SRC": str(self.src),
            "ROUTE": str(self.route),
            "START": self.start,
            "ISSUE": "852",
            "LATEST": "0.3.268",
            "BRANCH": "inspect-update/852/0.3.268",
            "REPO": "meridianlabs-ai/inspect_flow",
            "RUN_ID": "35921391185",
            "RUN_URL": "https://github.com/meridianlabs-ai/inspect_flow/actions/runs/35921391185",
            "ARTIFACT": _attempt_name(
                _land_steps()["route"]["env"]["ARTIFACT"], attempt
            ),
            "URL": str(self.origin),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "PLACEHOLDER": _placeholder(),
        }
        result = subprocess.run(
            ["bash", "-c", _land_steps()["route"]["run"]],
            cwd=self.tmp,
            env=env,
            capture_output=True,
            text=True,
        )
        outputs = dict(
            line.split("=", 1) for line in self.output.read_text().splitlines()
        )
        return result, outputs

    def draft(
        self, head: str, pulls: list[dict[str, Any]] | None = None, fail_on: str = ""
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, str], list[str]]:
        """Run the draft PR step against the local origin and the stub gh; return
        the process, the step outputs and the gh calls it made."""
        step = _land_steps()["draft"]
        pulls_file = self.tmp / "pulls.json"
        pulls_file.write_text(json.dumps(pulls or []))
        log = self.tmp / "gh-calls.log"
        log.unlink(missing_ok=True)
        self.output.write_text("")
        env = {
            "PATH": f"{GH_STUB}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(self.tmp),
            "GITHUB_OUTPUT": str(self.output),
            "RUNNER_TEMP": str(self.route.parent),
            "GH_STUB_LOG": str(log),
            "GH_STUB_PULLS": str(pulls_file),
            "GH_STUB_PR_URL": DRAFT_URL,
            **({"GH_STUB_FAIL_ON": fail_on} if fail_on else {}),
            "PLACEHOLDER": _placeholder(),
            "REPO": "meridianlabs-ai/inspect_flow",
            "ISSUE": "852",
            "LATEST": "0.3.268",
            "BRANCH": "inspect-update/852/0.3.268",
            "START": self.start,
            "HEAD": head,
            "RUN_ID": "35921391185",
            "RUN_URL": "https://github.com/meridianlabs-ai/inspect_flow/actions/runs/35921391185",
            "ARTIFACT": "inspect-update-handoff-1",
            "WORK": str(self.route.parent / "draft"),
            "URL": str(self.origin),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            **{
                k: v
                for k, v in step["env"].items()
                if k.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_"))
            },
        }
        result = subprocess.run(
            ["bash", "-c", step["run"]],
            cwd=self.tmp,
            env=env,
            capture_output=True,
            text=True,
        )
        outputs = dict(
            line.split("=", 1) for line in self.output.read_text().splitlines()
        )
        return result, outputs, log.read_text().splitlines() if log.exists() else []


DRAFT_URL = "https://github.com/meridianlabs-ai/inspect_flow/pull/901"
DRAFT_BRANCH = "inspect-update/852/0.3.268"


def _placeholder() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    return workflow["jobs"]["land"]["env"]["PLACEHOLDER"]


@pytest.fixture
def landing(tmp_path: Path) -> Landing:
    return Landing(tmp_path)


def _handoff_commands(comment: str, kept: Path) -> str:
    block = comment.split("### Inspect and apply", 1)[1].split("```sh\n", 1)[1]
    return block.split("```", 1)[0].replace("/tmp/inspect-update-852", str(kept))


def test_protected_changes_become_a_maintainer_handoff(landing: Landing) -> None:
    """Run 35921391185's shape: the marker advance and the lock upgrade (plus a
    source change) must not reach `land` as a push, and the kept commits must
    apply from the handoff comment's own commands."""
    _write(
        landing.agent,
        {
            "pyproject.toml": '[tool.inspect_flow]\ninspect-reconciled-version = "0.3.268"\n',
            "uv.lock": "b\n",
            "src/inspect_flow/x.py": "x = 1\n",
        },
    )
    head = _git(landing.agent, "rev-parse", "HEAD")
    landing.emit()

    result, outputs = landing.run()

    assert result.returncode == 0, result.stderr
    assert outputs == {"bundle": "true", "route": "handoff", "head": head}
    kept = landing.route / "handoff"
    assert sorted(f.name for f in kept.iterdir()) == [
        "changes.patch",
        "commits.bundle",
        "pr-body.md",
        "pr-title.txt",
    ]
    staged = landing.route / "landing"
    assert not (staged / "commits.bundle").exists()
    manifest = json.loads((staged / "manifest.json").read_text())
    assert "pr" not in manifest
    assert manifest["has_bundle"] is False
    assert manifest["head_sha"] == manifest["start_sha"] == landing.start
    assert manifest["comments"] == [
        {"number": 852, "body_file": "issue-comment.md"},
        {"number": 852, "body_file": "maintainer-handoff.md"},
    ]
    assert (staged / "issue-comment.md").read_text() == "## Mapping\n"

    comment = (staged / "maintainer-handoff.md").read_text()
    assert comment.startswith("@ransomr: **maintainer review needed.**")
    assert "not a failed run" in comment
    assert "None of these commits was pushed" in comment
    assert "no PR was opened" not in comment
    assert (
        "Protected, and the reason this needs you: `pyproject.toml`, `uv.lock`."
        in comment
    )
    assert "| `src/inspect_flow/x.py` | 1 | 0 |" in comment
    assert (
        "gh run download 35921391185 --repo meridianlabs-ai/inspect_flow "
        "--name inspect-update-handoff-1 --dir" in comment
    )
    assert "`Fixes #852`" in comment and "labelled `inspect-update`" in comment
    assert "draft PR from `inspect-update/852/0.3.268`" in comment
    assert "`maintainer-handoff` label" in comment
    assert "@auto" not in comment and "@review" not in comment

    # The maintainer's side: on the draft PR's branch in a clone of origin, the
    # comment's commands verbatim (the download directory aside) give the
    # agent's tree without the placeholder.
    draft, _, _ = landing.draft(head)
    assert draft.returncode == 0, draft.stderr
    maintainer = landing.tmp / "maintainer"
    _git(landing.tmp, "clone", "-q", str(landing.origin), str(maintainer))
    subprocess.run(
        ["bash", "-euo", "pipefail", "-c", _handoff_commands(comment, kept)],
        cwd=maintainer,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(landing.tmp),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "m",
            "GIT_AUTHOR_EMAIL": "m@m",
            "GIT_COMMITTER_NAME": "m",
            "GIT_COMMITTER_EMAIL": "m@m",
        },
        capture_output=True,
        check=True,
    )
    assert _git(maintainer, "branch", "--show-current") == DRAFT_BRANCH
    assert _git(maintainer, "rev-parse", "HEAD^{tree}") == _git(
        maintainer, "rev-parse", f"{head}^{{tree}}"
    )
    assert _git(maintainer, "merge-base", "--is-ancestor", head, "HEAD") == ""
    assert _placeholder() not in _git(maintainer, "ls-files").split()
    # The patch is the same change, for review or `git am`.
    _git(maintainer, "checkout", "-q", "-b", "am", landing.start)
    _git(
        maintainer,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "am",
        "-q",
        str(kept / "changes.patch"),
    )
    assert _git(maintainer, "rev-parse", "HEAD^{tree}") == _git(
        maintainer, "rev-parse", f"{head}^{{tree}}"
    )


def test_unprotected_changes_land_as_before(landing: Landing) -> None:
    _write(landing.agent, {"src/inspect_flow/x.py": "x = 1\n"})
    landing.emit()

    result, outputs = landing.run()

    assert result.returncode == 0, result.stderr
    assert outputs == {"bundle": "true"}
    assert "No protected path changed" in result.stdout
    assert (landing.route / "handoff/commits.bundle").exists()
    assert not (landing.route / "landing").exists()


def test_no_commits_route_nothing(landing: Landing) -> None:
    landing.emit()

    result, outputs = landing.run()

    assert result.returncode == 0, result.stderr
    assert outputs == {}
    assert "carries no commits" in result.stdout
    assert not (landing.route / "handoff").exists()


@pytest.mark.parametrize("field", ["start", "head"])
def test_commits_not_from_the_run_start_are_left_to_land(
    landing: Landing, field: str
) -> None:
    """A manifest naming another start, or a bundle whose tip is not its
    head_sha, is not the run's work: `land` gets it unchanged and refuses it."""
    _write(landing.agent, {"uv.lock": "b\n"})
    other = _git(landing.agent, "rev-parse", "HEAD")
    _write(landing.agent, {"uv.lock": "c\n"})
    if field == "start":
        landing.emit(start=other)
    else:
        landing.emit(head=other)

    result, outputs = landing.run()

    assert result.returncode == 0, result.stderr
    assert outputs == {}
    assert not (landing.route / "landing").exists()


def test_a_corrupt_bundle_fails_the_step_without_routing(landing: Landing) -> None:
    _write(landing.agent, {"uv.lock": "b\n"})
    landing.emit()
    (landing.src / "commits.bundle").write_bytes(b"not a bundle")

    result, outputs = landing.run()

    assert result.returncode != 0
    assert outputs == {}


def test_an_unreadable_protected_list_fails_closed_to_the_maintainer(
    landing: Landing,
) -> None:
    _write(landing.agent, {"src/inspect_flow/x.py": "x = 1\n"})
    landing.emit()
    landing.lib.unlink()

    result, outputs = landing.run()

    assert result.returncode == 0, result.stderr
    assert outputs == {
        "bundle": "true",
        "route": "handoff",
        "head": _git(landing.agent, "rev-parse", "HEAD"),
    }
    assert "treating every changed path as protected" in result.stdout


def test_agent_chosen_path_names_are_not_rendered(landing: Landing) -> None:
    _write(
        landing.agent,
        {
            "uv.lock": "b\n",
            "src/@auto `x`.py": "x = 1\n",
            "a/@review/pyproject.toml": "",
        },
    )
    landing.emit()

    result, outputs = landing.run()

    assert result.returncode == 0, result.stderr
    assert outputs["route"] == "handoff"
    comment = (landing.route / "landing/maintainer-handoff.md").read_text()
    assert "`uv.lock`, 1 path(s) with other characters (see the patch)" in comment
    assert "| 2 more (see the patch) | | |" in comment
    assert "@auto" not in comment and "@review" not in comment


def _attempt_name(expression: str, attempt: int) -> str:
    return expression.replace("${{ github.run_attempt }}", str(attempt))


def test_land_gets_the_staged_landing_only_after_the_commits_are_kept() -> None:
    steps = _land_steps()
    assert steps["keep"]["if"] == "steps.route.outputs.bundle == 'true'"
    assert steps["keep"]["with"]["retention-days"] == 90
    assert steps["stage"]["if"] == (
        "steps.route.outputs.route == 'handoff' && steps.keep.outcome == 'success'"
    )
    assert steps["land"]["with"]["artifact-name"] == (
        "${{ steps.stage.outcome == 'success' && "
        "format('landing-handoff-{0}', github.run_attempt) || 'landing' }}"
    )
    assert _attempt_name(steps["stage"]["with"]["name"], 2) == "landing-handoff-2"
    # The shared guard is still what decides a push: land keeps its trusted
    # start and pins, whichever artifact it gets.
    assert steps["land"]["uses"] == "meridianlabs-ai/agents/.github/actions/land@main"
    assert steps["land"]["with"]["start-sha"] == "${{ github.sha }}"
    assert steps["land"]["with"]["allowed-pr-labels"] == '["inspect-update"]'


def _run_land_step(
    name: str, tmp_path: Path, env: dict[str, str], fail: bool = False
) -> tuple[subprocess.CompletedProcess[str], str]:
    log = tmp_path / "gh-calls.log"
    result = subprocess.run(
        ["bash", "-c", _steps("land")[name]["run"]],
        cwd=tmp_path,
        env={
            "PATH": f"{GH_STUB}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "GH_STUB_LOG": str(log),
            "REPO": "meridianlabs-ai/inspect_flow",
            "ISSUE": "852",
            **({"GH_STUB_FAIL": "1"} if fail else {}),
            **env,
        },
        capture_output=True,
        text=True,
    )
    return result, log.read_text() if log.exists() else ""


def test_the_handoff_labels_the_issue(tmp_path: Path) -> None:
    result, calls = _run_land_step(
        "Hold newer releases for the maintainer", tmp_path, {}
    )

    assert result.returncode == 0, result.stderr
    assert calls.splitlines()[0].startswith(
        "label create maintainer-handoff --repo meridianlabs-ai/inspect_flow"
    )
    assert calls.splitlines()[-1] == (
        "issue edit 852 --repo meridianlabs-ai/inspect_flow --add-label maintainer-handoff"
    )


def test_a_failed_handoff_label_fails_the_run(tmp_path: Path) -> None:
    result, _ = _run_land_step(
        "Hold newer releases for the maintainer", tmp_path, {}, fail=True
    )

    assert result.returncode == 1
    assert "::error::Could not label #852 maintainer-handoff" in result.stdout


def test_a_rerun_never_replaces_an_earlier_attempts_kept_commits(
    landing: Landing,
) -> None:
    """upload-artifact's `overwrite` deletes the existing artifact before the new
    upload, so a re-run of the land job could leave an earlier attempt's handoff
    comment pointing at nothing. Each attempt keeps its own archive, and each
    comment names the one its attempt kept."""
    steps = _land_steps()
    for step in ("keep", "stage"):
        assert "overwrite" not in steps[step]["with"]
    keep = steps["keep"]["with"]["name"]
    report = _steps("land")["Report the failure on the release issue"]["env"]
    assert keep == steps["route"]["env"]["ARTIFACT"] == report["ARTIFACT"]

    _write(landing.agent, {"uv.lock": "b\n"})
    landing.emit()
    comments = []
    for attempt in (1, 2):
        result, outputs = landing.run(attempt)
        assert outputs["route"] == "handoff", result.stderr
        comments.append((landing.route / "landing/maintainer-handoff.md").read_text())

    assert _attempt_name(keep, 1) == "inspect-update-handoff-1"
    assert "--name inspect-update-handoff-1 --dir" in comments[0]
    assert "--name inspect-update-handoff-2 --dir" in comments[1]


REPORT_STEP = "Report the failure on the release issue"


def _selected(condition: str, context: dict[str, str]) -> bool:
    """Evaluate a step's `if:` built from always(), &&, ||, ==, != and step
    outcomes (an outcome absent from `context` is a skipped step's empty
    string)."""
    python = condition.replace("always()", "True")
    python = python.replace("&&", " and ").replace("||", " or ")
    python = re.sub(
        r"\bsteps\.[\w.-]+", lambda m: repr(context.get(m.group(0), "")), python
    )
    return bool(eval(python, {"__builtins__": {}}))


def _report(
    tmp_path: Path,
    land: str,
    hold: str = "",
    handoff: str = "",
    kept: str = "",
    draft: str = "",
    draft_pr: str = "",
    pr_number: str = "",
) -> tuple[bool, str]:
    """Whether the report step runs for these outcomes, and what it posts."""
    selected = _selected(
        _steps("land")[REPORT_STEP]["if"],
        {
            "steps.mint.outcome": "success",
            "steps.land.outcome": land,
            "steps.land.outputs.pr_number": pr_number,
            "steps.hold.outcome": hold,
            "steps.draft.outcome": draft,
        },
    )
    result, calls = _run_land_step(
        REPORT_STEP,
        tmp_path,
        {
            "LATEST": "0.3.268",
            "AGENT_RESULT": "success",
            "LAND_OUTCOME": land,
            "HOLD_OUTCOME": hold,
            "DRAFT_OUTCOME": draft,
            "DRAFT_PR": draft_pr,
            "PR_NUMBER": pr_number,
            "BRANCH": DRAFT_BRANCH,
            "HANDOFF": handoff,
            "RUN_URL": "https://github.com/x/runs/1",
            "RUN_ID": "35921391185",
            "KEPT": kept,
            "ARTIFACT": "inspect-update-handoff-1",
        },
    )
    assert result.returncode == 0, result.stderr
    assert calls.startswith("issue comment 852 --repo meridianlabs-ai/inspect_flow")
    return selected, calls


@pytest.mark.parametrize("kept", ["true", ""])
def test_failure_report_names_the_kept_commits(tmp_path: Path, kept: str) -> None:
    selected, body = _report(tmp_path, land="failure", kept=kept)

    assert selected
    assert "until this issue is retitled or deleted" in body
    assert "maintainer-handoff" not in body
    line = (
        "kept for 90 days as the `inspect-update-handoff-1` artifact of this run "
        "(`gh run download 35921391185 --repo meridianlabs-ai/inspect_flow "
        "--name inspect-update-handoff-1`)"
    )
    assert (line in body) == bool(kept)


def test_a_failed_hold_label_is_reported_after_a_successful_landing(
    tmp_path: Path,
) -> None:
    """The handoff comment says newer releases wait; when the label that makes
    that true could not be added, the issue has to say so, not only the log."""
    selected, body = _report(
        tmp_path, land="success", hold="failure", handoff="true", kept="true"
    )

    assert selected
    assert "did not complete" not in body
    assert "handed its commits to the maintainer, but a step after" in body
    assert "The `maintainer-handoff` label could not be added" in body
    assert (
        "`gh issue edit 852 --repo meridianlabs-ai/inspect_flow "
        "--add-label maintainer-handoff`" in body
    )
    assert "`inspect-update-handoff-1` artifact" in body


@pytest.mark.parametrize(("hold", "draft"), [("success", "success"), ("", "")])
def test_a_clean_landing_posts_no_failure_report(
    tmp_path: Path, hold: str, draft: str
) -> None:
    selected, _ = _report(
        tmp_path, land="success", hold=hold, handoff="true", draft=draft
    )
    assert not selected


def test_handoff_failure_recovery_clears_the_hold_as_well_as_the_claim(
    tmp_path: Path,
) -> None:
    """A handoff whose landing failed carries the hold label: retitling the issue
    clears the version claim but not the hold, so the report says to remove the
    label too, and the gate proceeds only once both are done."""
    selected, body = _report(
        tmp_path,
        land="failure",
        hold="success",
        handoff="true",
        kept="true",
        draft="success",
        draft_pr=DRAFT_URL,
    )
    assert selected
    assert "retitled or not" in body
    assert f"add it to the draft PR {DRAFT_URL}, or open your own PR" in body
    assert (
        "remove the `maintainer-handoff` label as well as retitling or deleting "
        "this issue, and close the draft PR if one was opened" in body
    )

    retitled = _issue(852, "Abandoned reconciliation attempt")
    decisions = {}
    for name, handoffs in (("retitled", [retitled]), ("recovered", [])):
        (tmp_path / name).mkdir()
        result, outputs, _ = _run_gate(
            tmp_path / name,
            pulls=[[]],
            issues=[[retitled]],
            latest="0.3.268",
            reconciled="0.3.266",
            handoffs=handoffs,
        )
        assert result.returncode == 0, result.stderr
        decisions[name] = outputs["proceed"]
    assert decisions == {"retitled": "false", "recovered": "true"}


def test_the_agent_is_told_protected_commits_go_to_the_maintainer() -> None:
    prompt = _prompt()
    assert "are never\npushed by automation" in prompt
    assert "hands them to the\nmaintainer" in prompt


def _handoff(landing: Landing) -> str:
    """Route run 35921391185's shape to a handoff; return the verified tip."""
    _write(landing.agent, {"uv.lock": "b\n", "src/inspect_flow/x.py": "x = 1\n"})
    landing.emit()
    result, outputs = landing.run()
    assert outputs["route"] == "handoff", result.stderr
    return outputs["head"]


def _origin_branch(landing: Landing) -> str:
    return _git(
        landing.origin,
        "for-each-ref",
        "--format=%(objectname)",
        f"refs/heads/{DRAFT_BRANCH}",
    )


def test_the_draft_pr_carries_only_the_placeholder(landing: Landing) -> None:
    """The branch the draft PR needs is github.sha plus the placeholder note: no
    object of the agent's commits (the protected uv.lock above all) reaches
    origin, and the note and PR body name the kept artifact and run, from
    trusted values only."""
    head = _handoff(landing)

    result, outputs, calls = landing.draft(head)

    assert result.returncode == 0, result.stderr
    assert outputs == {"pr": DRAFT_URL}
    tip = _origin_branch(landing)
    assert _git(landing.origin, "rev-parse", f"{tip}^") == landing.start
    assert _git(landing.origin, "diff", "--name-status", landing.start, tip) == (
        f"A\t{_placeholder()}"
    )
    lock = _git(landing.agent, "rev-parse", f"{head}:uv.lock")
    for obj in (head, lock):
        missing = subprocess.run(
            ["git", "cat-file", "-e", obj], cwd=landing.origin, capture_output=True
        )
        assert missing.returncode != 0, f"{obj} reached origin"
    assert _git(landing.origin, "log", "-1", "--format=%an", tip) == (
        "meridian-marvin[bot]"
    )

    note = _git(landing.origin, "show", f"{tip}:{_placeholder()}")
    body = (landing.route.parent / "draft-body.md").read_text()
    for text in (note, body):
        assert "`inspect-update-handoff-1` artifact of [run 35921391185]" in text
        assert f"`{landing.start}..{head}`" in text or (
            f"from `{landing.start}` to `{head}`" in text
        )
        assert "Agent PR body" not in text and "chore: reconcile" not in text
        for trigger in ("@auto", "@review", "@claude"):
            assert trigger not in text
    assert "**Delete this file before merging**" in note
    assert body.startswith("Fixes #852\n\n**Maintainer handoff, not mergeable as is.**")

    assert calls[0].split()[:2] == [
        "api",
        "repos/meridianlabs-ai/inspect_flow/pulls?state=all&head=meridianlabs-ai:"
        f"{DRAFT_BRANCH}&per_page=100",
    ]
    assert calls[1].startswith(
        "pr create --draft --repo meridianlabs-ai/inspect_flow --base main "
        f"--head {DRAFT_BRANCH} --title chore: reconcile inspect-ai 0.3.268 "
        "(maintainer handoff) --body-file "
    )
    assert calls[2:] == [
        f"pr edit {DRAFT_URL} --repo meridianlabs-ai/inspect_flow "
        "--add-label inspect-update --add-assignee ransomr"
    ]


@pytest.mark.parametrize(("state", "edited"), [("open", True), ("closed", False)])
def test_a_rerun_adopts_the_pr_from_the_branch(
    landing: Landing, state: str, edited: bool
) -> None:
    """One handoff PR per release: an attempt that finds a PR from the branch,
    open or closed, pushes nothing and opens nothing; an open one is labelled
    and assigned again (an earlier attempt may have failed there)."""
    head = _handoff(landing)
    other = {"html_url": f"{DRAFT_URL}0", "state": "closed"}
    pr = {"html_url": DRAFT_URL, "state": state}

    result, outputs, calls = landing.draft(head, pulls=[other, pr])

    assert result.returncode == 0, result.stderr
    assert outputs == {"pr": DRAFT_URL if state == "open" else f"{DRAFT_URL}0"}
    assert f"Adopting {outputs['pr']} ({state})" in result.stdout
    assert _origin_branch(landing) == ""
    assert not any(c.startswith("pr create") for c in calls)
    assert any(c.startswith(f"pr edit {DRAFT_URL} ") for c in calls) == edited


def test_a_partial_failure_is_reported_and_the_rerun_adopts_the_branch(
    tmp_path: Path, landing: Landing
) -> None:
    head = _handoff(landing)

    failed, outputs, _ = landing.draft(head, fail_on="pr create")

    assert failed.returncode != 0
    assert outputs == {}
    pushed = _origin_branch(landing)
    assert pushed != ""
    (tmp_path / "report").mkdir()
    selected, body = _report(
        tmp_path / "report",
        land="success",
        hold="success",
        handoff="true",
        draft="failure",
    )
    assert selected
    assert "handed its commits to the maintainer, but a step after" in body
    assert "The draft PR for this handoff could not be opened" in body
    assert f"adopts the branch `{DRAFT_BRANCH}`" in body
    assert (
        "`gh pr create --draft --repo meridianlabs-ai/inspect_flow --base main "
        f'--head {DRAFT_BRANCH} --title "chore: reconcile inspect-ai 0.3.268 '
        '(maintainer handoff)" --body "Fixes #852"`' in body
    )

    result, outputs, calls = landing.draft(head)

    assert result.returncode == 0, result.stderr
    assert outputs == {"pr": DRAFT_URL}
    assert f"Adopting the branch {DRAFT_BRANCH} already on origin" in result.stdout
    assert _origin_branch(landing) == pushed
    assert [c.split()[:2] for c in calls[1:]] == [["pr", "create"], ["pr", "edit"]]


def test_a_failed_label_after_the_draft_is_opened_fails_the_step(
    landing: Landing,
) -> None:
    head = _handoff(landing)

    result, outputs, _ = landing.draft(head, fail_on="pr edit")

    assert result.returncode != 0
    assert outputs == {"pr": DRAFT_URL}


@pytest.mark.parametrize("head", ["", "HEAD", "a" * 39])
def test_the_draft_is_composed_only_from_expected_values(
    landing: Landing, head: str
) -> None:
    _handoff(landing)

    result, outputs, calls = landing.draft(head)

    assert result.returncode != 0
    assert "Refusing to compose the draft PR" in result.stdout
    assert outputs == {} and calls == []
    assert _origin_branch(landing) == ""


def test_only_a_staged_handoff_opens_a_draft_pr() -> None:
    """Unprotected commits land as before (land opens their PR) and a run with
    no commits or an unverified bundle has nothing to hand off."""
    condition = _land_steps()["draft"]["if"]
    context = {"steps.mint.outcome": "success"}
    assert _selected(condition, {**context, "steps.stage.outcome": "success"})
    for stage in ("", "failure"):
        assert not _selected(condition, {**context, "steps.stage.outcome": stage})


def test_no_maintainer_handoff_placeholder_in_the_tree() -> None:
    """The draft PR of a maintainer handoff holds only this note until the
    maintainer adds the reviewed commits; failing here, in the required py-test
    checks, keeps that PR from merging with the note still in it."""
    placeholder = WORKFLOWS.parent.parent / _placeholder()
    assert not placeholder.exists(), (
        f"Delete {placeholder.name}: it is the maintainer handoff's placeholder."
    )


def test_a_draft_opened_without_its_label_is_reported(tmp_path: Path) -> None:
    selected, body = _report(
        tmp_path,
        land="success",
        hold="success",
        handoff="true",
        draft="failure",
        draft_pr=DRAFT_URL,
    )

    assert selected
    assert "could not be opened" not in body
    assert (
        f"The draft PR for this handoff, {DRAFT_URL}, was opened, but its "
        "`inspect-update` label or assignee could not be added: `gh pr edit "
        f"{DRAFT_URL} --repo meridianlabs-ai/inspect_flow --add-label "
        "inspect-update --add-assignee ransomr`." in body
    )


@pytest.mark.parametrize(
    ("workflow", "job"),
    [("inspect-update.yml", "land"), ("inspect-ai-main-failure.yml", "triage-land")],
)
def test_land_opens_a_draft_assigned_to_the_maintainer(workflow: str, job: str) -> None:
    """The agents behind these PRs read third-party text (a failed run's logs,
    inspect-ai's changelog), so land opens their PRs as drafts for ransomr's
    review (agents#175) and neither allows the `auto` label (#859)."""
    land = _steps(job, WORKFLOWS / workflow)["Land"]["with"]
    assert land["pr-draft"] == "true"
    assert land["pr-assignees"] == "ransomr"
    assert "auto" not in json.loads(land["allowed-pr-labels"])


def test_a_landing_that_failed_after_opening_the_pr_keeps_it(tmp_path: Path) -> None:
    """land fails the run when the PR's assignee (or a comment) did not take,
    after it opened the PR: the release issue points at that PR rather than
    telling the maintainer to close it and start again."""
    selected, body = _report(tmp_path, land="failure", pr_number="861")

    assert selected
    assert "opened #861, but a landing step after it failed" in body
    assert "The note on #861 names what failed, such as its assignee" in body
    assert "review the PR as usual" in body
    assert "did not complete" not in body


def test_a_canary_pr_whose_assignee_did_not_take_is_still_triaged() -> None:
    """The canary's land fails the run over a failed assignment after it opened
    the PR; the issue is still marked triaged, or the next canary failure
    re-triages and opens a duplicate PR, and the failure is reported."""
    steps = _steps("triage-land", WORKFLOWS / "inspect-ai-main-failure.yml")
    context = {
        "steps.mint.outcome": "success",
        "steps.land.outcome": "failure",
        "steps.land.outputs.pr_number": "861",
    }
    assert _selected(steps["Apply the triage labels"]["if"], context)
    context["steps.labels.outcome"] = "success"
    assert _selected(steps["Report the failure on the tracking issue"]["if"], context)
