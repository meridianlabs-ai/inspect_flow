from pathlib import Path

import pytest
from inspect_flow._util.path_util import (
    apply_bundle_url_mappings,
    cwd_relative_path,
    path_str,
)


def test_apply_bundle_url_mappings_trailing_slash_on_value() -> None:
    # Reproduces a double-slash bug: the launcher strips trailing slashes from
    # mapping keys via absolute_path_relative_to, but values retain their trailing
    # slash. The result should not contain a double slash.
    result = apply_bundle_url_mappings(
        "s3://flow-view/bundle",
        {"s3://flow-view": "http://flow-view.s3-website.us-east-2.amazonaws.com/"},
    )
    assert result == "http://flow-view.s3-website.us-east-2.amazonaws.com/bundle"
    assert "//" not in result.removeprefix("http://")


def test_cwd_relative_path_only_strips_cwd_at_separator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A sibling directory whose name starts with the cwd's name must not be
    # treated as being inside the cwd (e.g. cwd "proj" and log_dir "proj-logs").
    cwd = tmp_path / "proj"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cwd_str = Path.cwd().as_posix()
    sibling = cwd_str + "-logs"

    assert cwd_relative_path(sibling) == sibling
    assert path_str(sibling) == sibling
    assert path_str(f"file://{sibling}/x.eval") == f"{sibling}/x.eval"
    assert cwd_relative_path(f"{cwd_str}/logs") == "logs"
    assert path_str(f"file://{cwd_str}/logs/x.eval") == "logs/x.eval"
