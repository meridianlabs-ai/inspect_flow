import click
import pytest
from click.testing import CliRunner
from inspect_flow._cli.constants import resolve_tokens
from inspect_flow._cli.main import flow

FIXTURES = "tests/config/constants"


def test_passthrough_non_at_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    assert resolve_tokens(["run", "--flag", "s3://logs"]) == [
        "run",
        "--flag",
        "s3://logs",
    ]


def test_no_discovery_when_no_at_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """No _flow.py load happens when no @ token is present."""
    monkeypatch.chdir(FIXTURES)
    import inspect_flow._cli.constants as mod

    called = False

    def _boom() -> dict[str, list[tuple[str, str]]]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(mod, "_discover_constants", _boom)
    resolve_tokens(["--add", "plain", "s3://logs"])
    assert called is False


def test_resolve_bare_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    assert resolve_tokens(["@LOG_DIR_DEV"]) == ["s3://dev/logs"]


def test_resolve_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    with pytest.raises(click.BadParameter, match="UNKNOWN_CONSTANT"):
        resolve_tokens(["@UNKNOWN_CONSTANT"])


def test_collision_with_different_values_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(f"{FIXTURES}/sub")
    with pytest.raises(click.BadParameter, match="multiple files"):
        resolve_tokens(["@TAG_QA_NEEDED"])


def test_collision_with_same_value_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same name in parent and child with same value is not an error."""
    monkeypatch.chdir(f"{FIXTURES}/sub")
    assert resolve_tokens(["@SHARED_SAME"]) == ["shared_value"]


def test_parent_only_discovered_from_child(monkeypatch: pytest.MonkeyPatch) -> None:
    """Parent _flow.py constants are visible when cwd is a child dir."""
    monkeypatch.chdir(f"{FIXTURES}/sub")
    assert resolve_tokens(["@LOG_DIR_DEV"]) == ["s3://dev/logs"]


def test_child_only_not_discovered_from_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child _flow.py constants are NOT visible when cwd is the parent."""
    monkeypatch.chdir(FIXTURES)
    with pytest.raises(click.BadParameter, match="SUB_ONLY"):
        resolve_tokens(["@SUB_ONLY"])


def test_file_scope_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    assert resolve_tokens(["@explicit_module.py@FROM_FILE"]) == ["from_file_value"]


def test_file_scope_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    with pytest.raises(click.BadParameter, match="NOT_DEFINED"):
        resolve_tokens(["@explicit_module.py@NOT_DEFINED"])


def test_file_scope_disambiguates_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """file.py@NAME form bypasses the global collision check."""
    monkeypatch.chdir(FIXTURES)
    assert resolve_tokens(["@sub/_flow.py@TAG_QA_NEEDED"]) == ["override_value"]
    assert resolve_tokens(["@_flow.py@TAG_QA_NEEDED"]) == ["qa_auto_needed"]


def test_file_scope_missing_file_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    with pytest.raises(click.BadParameter, match="File not found"):
        resolve_tokens(["@does_not_exist.py@X"])


@pytest.mark.parametrize(
    "token",
    [
        "@lower_case",
        "@MixedCase",
        "@_PRIVATE",
        "@INTEGER",
        "@STRING_LIST",
    ],
)
def test_exclusions(token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lowercase, mixed-case, underscore-prefixed, and non-string values are excluded."""
    monkeypatch.chdir(FIXTURES)
    with pytest.raises(click.BadParameter, match="not found"):
        resolve_tokens([token])


def test_multiple_tokens_mixed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    assert resolve_tokens(["--add", "@TAG_QA_NEEDED", "@LOG_DIR_DEV", "literal"]) == [
        "--add",
        "qa_auto_needed",
        "s3://dev/logs",
        "literal",
    ]


def test_cli_wiring_resolves_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: FlowGroup.parse_args runs resolve_tokens before Click parses."""
    monkeypatch.chdir(FIXTURES)
    runner = CliRunner()
    result = runner.invoke(flow, ["step", "@UNDEFINED_IN_FIXTURES"])
    assert result.exit_code != 0
    assert "UNDEFINED_IN_FIXTURES" in str(result.output) + str(result.exception)
