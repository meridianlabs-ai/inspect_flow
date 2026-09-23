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
kept bundle applies from the handoff comment's own commands, while other
commits are left to land as before.
"""

import json
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
        if any(
            step.get("uses", "").startswith("anthropics/claude-code-action")
            for step in job.get("steps", [])
        )
    }
    assert agent_jobs == {
        ("inspect-update.yml", "agent"): "read",
        ("inspect-ai-main-failure.yml", "triage-agent"): "read",
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

    def run(self) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
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
            "URL": str(self.origin),
            "GIT_CONFIG_GLOBAL": "/dev/null",
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
    assert outputs == {"bundle": "true", "route": "handoff"}
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
    assert (
        "Protected, and the reason this needs you: `pyproject.toml`, `uv.lock`."
        in comment
    )
    assert "| `src/inspect_flow/x.py` | 1 | 0 |" in comment
    assert (
        "gh run download 35921391185 --repo meridianlabs-ai/inspect_flow "
        "--name inspect-update-handoff" in comment
    )
    assert "`Fixes #852`" in comment and "`inspect-update` label" in comment
    assert "`maintainer-handoff` label" in comment
    assert "@auto" not in comment and "@review" not in comment

    # The maintainer's side: a clone of origin, the comment's commands verbatim
    # (the download directory aside), ends on the agent's tip.
    maintainer = landing.tmp / "maintainer"
    _git(landing.tmp, "clone", "-q", str(landing.origin), str(maintainer))
    subprocess.run(
        ["bash", "-euo", "pipefail", "-c", _handoff_commands(comment, kept)],
        cwd=maintainer,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(landing.tmp),
            "GIT_CONFIG_GLOBAL": "/dev/null",
        },
        capture_output=True,
        check=True,
    )
    assert _git(maintainer, "rev-parse", "HEAD") == head
    assert _git(maintainer, "branch", "--show-current") == "inspect-update/852/0.3.268"
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
    assert outputs == {"bundle": "true", "route": "handoff"}
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


def test_land_gets_the_staged_landing_only_after_the_commits_are_kept() -> None:
    steps = _land_steps()
    assert steps["keep"]["if"] == "steps.route.outputs.bundle == 'true'"
    assert steps["keep"]["with"]["name"] == "inspect-update-handoff"
    assert steps["keep"]["with"]["retention-days"] == 90
    assert steps["stage"]["if"] == (
        "steps.route.outputs.route == 'handoff' && steps.keep.outcome == 'success'"
    )
    assert steps["land"]["with"]["artifact-name"] == (
        "${{ steps.stage.outcome == 'success' && 'landing-handoff' || 'landing' }}"
    )
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


@pytest.mark.parametrize("kept", ["true", ""])
def test_failure_report_names_the_kept_commits(tmp_path: Path, kept: str) -> None:
    result, calls = _run_land_step(
        "Report the failure on the release issue",
        tmp_path,
        {
            "LATEST": "0.3.268",
            "AGENT_RESULT": "success",
            "LAND_OUTCOME": "failure",
            "RUN_URL": "https://github.com/x/runs/1",
            "RUN_ID": "35921391185",
            "KEPT": kept,
        },
    )

    assert result.returncode == 0, result.stderr
    assert calls.startswith("issue comment 852 --repo meridianlabs-ai/inspect_flow")
    assert "until this issue is retitled or deleted" in calls
    line = (
        "kept for 90 days as the `inspect-update-handoff` artifact of this run "
        "(`gh run download 35921391185 --repo meridianlabs-ai/inspect_flow "
        "--name inspect-update-handoff`)"
    )
    assert (line in calls) == bool(kept)


def test_the_agent_is_told_protected_commits_go_to_the_maintainer() -> None:
    prompt = _prompt()
    assert "are never\npushed by automation" in prompt
    assert "hands them to the\nmaintainer" in prompt
