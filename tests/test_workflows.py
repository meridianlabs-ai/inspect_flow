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

Every call of the agents repo's reusable workflows sets the `provision` recipe
the agent user runs in place of claude-setup, with claude-setup's Python
(meridianlabs-ai/agents design/executed-paths-residual.md).
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
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], list[str]]:
    """Run the gate's dedup step against the stub gh; return the process, the
    step outputs and the gh calls it made. `--paginate` prints one array per
    page, so multi-page fixtures are concatenated documents."""
    pulls_file = tmp_path / "pulls.json"
    issues_file = tmp_path / "issues.json"
    pulls_file.write_text("\n".join(json.dumps(page) for page in pulls))
    issues_file.write_text("\n".join(json.dumps(page) for page in issues))
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
