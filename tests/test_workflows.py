"""Tests for the shell steps of .github/workflows/inspect-update.yml.

The `agent` job's "Surface agent errors" and "Compose landing manifest" steps
are run with bash against a fixture execution file shaped like the result
record claude-code-action writes (a `permission_denials` list of
`{tool_name, tool_use_id, tool_input}`), so a refused commit is reported on
the release issue instead of passing as a silent success (run 35446410455).
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).parent.parent / ".github/workflows/inspect-update.yml"

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


def _agent_steps() -> dict[str, dict[str, Any]]:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    return {
        step["name"]: step
        for step in workflow["jobs"]["agent"]["steps"]
        if "name" in step
    }


def _prompt() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    step = next(
        s for s in workflow["jobs"]["agent"]["steps"] if s.get("id") == "claude"
    )
    return step["with"]["prompt"]


def _run_step(name: str, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        ["bash", "-c", _agent_steps()[name]["run"]],
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
    assert comment.startswith(
        "## Mapping\n\nAll done.\n\n\n⚠️ 2 tool call(s) were refused"
    )
    assert "    Bash: git commit -m" in comment


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
