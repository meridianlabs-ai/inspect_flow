from pathlib import Path

import pytest
from inspect_ai.log import (
    EvalConfig,
    EvalDataset,
    EvalLog,
    EvalResults,
    EvalSample,
    EvalSpec,
    read_eval_log,
    write_eval_log,
)
from inspect_flow._steps.copy import copy
from inspect_flow._steps.run import run_step
from inspect_flow._steps.step import StepResult, step
from inspect_flow._steps.tag import metadata, tag


def _make_log(tmp_path: Path, name: str = "test.eval") -> str:
    log_path = str(tmp_path / name)
    samples = [
        EvalSample(id=1, epoch=1, input="hello", target="world", uuid="uuid-1"),
    ]
    log = EvalLog(
        status="success",
        eval=EvalSpec(
            created="2024-01-01T00:00:00+00:00",
            task="test_task",
            dataset=EvalDataset(),
            model="mockllm/model",
            config=EvalConfig(),
        ),
        results=EvalResults(total_samples=1, completed_samples=1),
        samples=samples,
    )
    write_eval_log(log, location=log_path)
    return log_path


# --- tag step ---


def test_tag_add_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    result = tag(log_path, add=["reviewed"])
    assert result is not None
    assert "reviewed" in (result.tags or [])
    # Verify written to disk
    reloaded = read_eval_log(log_path, header_only=True)
    assert "reviewed" in (reloaded.tags or [])


def test_tag_remove_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    tag(log_path, add=["draft"])
    result = tag(log_path, remove=["draft"])
    assert result is not None
    assert "draft" not in (result.tags or [])
    reloaded = read_eval_log(log_path, header_only=True)
    assert "draft" not in (reloaded.tags or [])


def test_tag_from_evallog(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    log = read_eval_log(log_path)
    result = tag(log, add=["golden"])
    assert result is not None
    assert "golden" in (result.tags or [])


# --- metadata step ---


def test_metadata_set_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    result = metadata(log_path, set={"score": 0.95})
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["score"] == 0.95
    reloaded = read_eval_log(log_path, header_only=True)
    assert reloaded.metadata is not None
    assert reloaded.metadata["score"] == 0.95


def test_metadata_remove_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    metadata(log_path, set={"key1": "val1", "key2": "val2"})
    result = metadata(log_path, remove=["key1"])
    assert result is not None
    assert result.metadata is not None
    assert "key1" not in result.metadata
    assert result.metadata["key2"] == "val2"


# --- copy step ---


def test_copy_flat(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    result = copy(log_path, dest=dest)
    assert result is not None
    assert result.location.startswith(dest)
    assert Path(result.location).name == "test.eval"
    reloaded = read_eval_log(result.location)
    assert reloaded.eval.task == "test_task"
    assert reloaded.samples is not None
    assert len(reloaded.samples) == 1


def test_copy_with_source_prefix(tmp_path: Path) -> None:
    src_dir = tmp_path / "src" / "subdir"
    src_dir.mkdir(parents=True)
    log_path = _make_log(src_dir)
    dest = str(tmp_path / "dest")
    prefix = str(tmp_path / "src")
    result = copy(log_path, dest=dest, source_prefix=prefix)
    assert result is not None
    assert "subdir/test.eval" in result.location


# --- chaining steps on a single log (design doc example) ---


def test_chain_tag_then_copy(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    log = read_eval_log(log_path)
    log = tag(log, add=["golden"], reason="Promoted")
    assert log is not None
    log = copy(log, dest=dest)
    assert log is not None
    # Destination log has the tag
    reloaded = read_eval_log(log.location)
    assert "golden" in (reloaded.tags or [])


# --- @step with deferred writes (design doc example) ---


def test_nested_step_defers_writes(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step(header_only=False)
    def promote(log: EvalLog, *, dest: str) -> EvalLog:
        log = tag(log, add=["golden"], reason="Promoted")
        assert log is not None
        return copy(log, dest=dest)

    dest = str(tmp_path / "dest")
    result = promote(log_path, dest=dest)
    assert result is not None
    # Source was written with tag
    reloaded_src = read_eval_log(log_path, header_only=True)
    assert "golden" in (reloaded_src.tags or [])
    # Destination was written
    reloaded_dest = read_eval_log(result.location)
    assert "golden" in (reloaded_dest.tags or [])
    assert reloaded_dest.samples is not None
    assert len(reloaded_dest.samples) == 1


# --- run_step across multiple logs ---


def test_run_step_directory(tmp_path: Path) -> None:
    _make_log(tmp_path, "log1.eval")
    _make_log(tmp_path, "log2.eval")
    run_step(tag, str(tmp_path), add=["batch"])
    for name in ["log1.eval", "log2.eval"]:
        reloaded = read_eval_log(str(tmp_path / name), header_only=True)
        assert "batch" in (reloaded.tags or [])


def test_run_step_with_list_of_paths(tmp_path: Path) -> None:
    path1 = _make_log(tmp_path, "a.eval")
    path2 = _make_log(tmp_path, "b.eval")
    run_step(tag, [path1, path2], add=["listed"])
    for path in [path1, path2]:
        reloaded = read_eval_log(path, header_only=True)
        assert "listed" in (reloaded.tags or [])


# --- header_only strips samples ---


def test_header_only_step_does_not_see_samples(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def check_no_samples(log: EvalLog) -> EvalLog:
        assert log.samples is None
        return log

    check_no_samples(log_path)


def test_header_only_false_step_sees_samples(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step(header_only=False)
    def check_has_samples(log: EvalLog) -> EvalLog:
        assert log.samples is not None
        assert len(log.samples) == 1
        return log

    check_has_samples(log_path)


# --- samples preserved after header_only step writes back ---


def test_header_only_step_preserves_samples_on_write(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    tag(log_path, add=["test"])
    reloaded = read_eval_log(log_path)
    assert reloaded.samples is not None
    assert len(reloaded.samples) == 1


# --- StepResult ---


def test_step_result_skip_log_steps(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def skip_step(log: EvalLog) -> StepResult:
        return StepResult(log=log, skip_log_steps=True)

    result = skip_step(log_path)
    assert result is None


def test_step_result_modified_false_does_not_write(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def read_only_step(log: EvalLog) -> StepResult:
        return StepResult(log=log, modified=False)

    result = read_only_step(log_path)
    assert result is not None
    # Log should not have been modified on disk — no tags added
    reloaded = read_eval_log(log_path, header_only=True)
    assert not reloaded.tags


def test_return_none_skips(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def none_step(log: EvalLog) -> None:
        return None

    result = none_step(log_path)
    assert result is None


# --- nested step receives path raises ---


def test_nested_step_with_path_raises(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def inner(log: EvalLog) -> EvalLog:
        return log

    @step
    def outer(log: EvalLog) -> EvalLog:
        return inner(log_path)

    with pytest.raises(ValueError, match="nested inside another step"):
        outer(log_path)


# --- _format_step_call ---


def test_format_step_call_basic() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert _format_step_call("tag", {"add": ["golden"]}) == "tag(add=['golden'])"


def test_format_step_call_hides_none() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert (
        _format_step_call("tag", {"add": ["golden"], "remove": None})
        == "tag(add=['golden'])"
    )


def test_format_step_call_hides_empty_sequences() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert (
        _format_step_call("tag", {"add": ["golden"], "remove": []})
        == "tag(add=['golden'])"
    )
    assert (
        _format_step_call("tag", {"add": ["golden"], "remove": ()})
        == "tag(add=['golden'])"
    )


def test_format_step_call_converts_tuples_to_lists() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert _format_step_call("tag", {"add": ("tag1",)}) == "tag(add=['tag1'])"


def test_format_step_call_no_args() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert _format_step_call("qa", {}) == "qa()"


# --- CLI help ---


def test_cli_tag_help() -> None:
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, ["tag", "--help"])
    assert result.exit_code == 0
    assert "--add" in result.output
    assert "--remove" in result.output
    assert "--author" in result.output
    assert "--reason" in result.output
    # Should NOT show raw *args/**kwargs
    assert "--args" not in result.output
    assert "--kwargs" not in result.output


def test_cli_copy_help() -> None:
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, ["copy", "--help"])
    assert result.exit_code == 0
    assert "--dest" in result.output
    assert "--source-prefix" in result.output
    assert "--args" not in result.output
    assert "--kwargs" not in result.output
