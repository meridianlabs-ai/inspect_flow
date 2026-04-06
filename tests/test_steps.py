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
from inspect_flow._store.deltalake import DeltaLakeStore
from rich.console import Console


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


# --- _relative_path ---


def test_relative_path_with_prefix() -> None:
    from inspect_flow._steps.copy import _relative_path

    assert _relative_path("/a/b/c/log.eval", "/a/b") == "c/log.eval"


def test_relative_path_without_prefix() -> None:
    from inspect_flow._steps.copy import _relative_path

    assert _relative_path("/a/b/c/log.eval", None) == "log.eval"


def test_relative_path_prefix_not_matching() -> None:
    from inspect_flow._steps.copy import _relative_path

    assert _relative_path("/a/b/c/log.eval", "/x/y") == "log.eval"


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


def test_copy_skips_existing(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    first = copy(log_path, dest=dest)
    assert first is not None
    second = copy(log_path, dest=dest)
    assert second is None


def test_copy_overwrite(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    first = copy(log_path, dest=dest)
    assert first is not None
    second = copy(log_path, dest=dest, overwrite=True)
    assert second is not None
    assert second.location == first.location


def test_copy_via_run_step_with_source_prefix(tmp_path: Path) -> None:
    """run_step expands paths via list_eval_logs which returns file:/// URIs.

    source_prefix must still match against the resulting log.location.
    """
    src_dir = tmp_path / "logs" / "subdir"
    src_dir.mkdir(parents=True)
    log_path = _make_log(src_dir)
    dest = str(tmp_path / "dest")
    prefix = str(tmp_path / "logs")
    run_step(copy, log_path, dest=dest, source_prefix=prefix)
    dest_file = Path(dest) / "subdir" / "test.eval"
    assert dest_file.exists()
    reloaded = read_eval_log(str(dest_file))
    assert reloaded.eval.task == "test_task"


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
    def promote(log: EvalLog, *, dest: str) -> EvalLog | None:
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


def test_run_step_no_logs(tmp_path: Path, recording_console: Console) -> None:
    run_step(tag, str(tmp_path), add=["batch"])
    captured = recording_console.export_text()
    assert "No logs found" in captured


def test_run_step_evallog_no_duplicate_header(
    tmp_path: Path, recording_console: Console
) -> None:
    log_path = _make_log(tmp_path)
    log = read_eval_log(log_path)
    run_step(tag, [log], add=["test"])
    captured = recording_console.export_text()
    header_lines = [line for line in captured.splitlines() if "(1 of 1)" in line]
    assert len(header_lines) == 1


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


def test_nested_header_only_step_preserves_samples(tmp_path: Path) -> None:
    """A header_only step that calls another header_only step (e.g. tag)
    must not destroy samples on disk."""
    log_path = _make_log(tmp_path)

    @step
    def qa(log: EvalLog) -> EvalLog:
        result = tag(log, add=["qa_passed"])
        assert result is not None
        return result

    qa(log_path)
    reloaded = read_eval_log(log_path)
    assert "qa_passed" in (reloaded.tags or [])
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


def test_nested_step_with_different_path_raises(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path, "outer.eval")
    other_path = _make_log(tmp_path, "other.eval")

    @step
    def inner(log: EvalLog) -> EvalLog:
        return log

    @step
    def outer(log: EvalLog) -> EvalLog:
        return inner(other_path)

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


# --- CLI metadata --set ---


def test_cli_metadata_set(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command,
        ["metadata", log_path, "--set", "score_threshold=0.9"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    reloaded = read_eval_log(log_path, header_only=True)
    assert reloaded.metadata is not None
    assert reloaded.metadata["score_threshold"] == "0.9"


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
    assert "--dry-run" in result.output
    # Should NOT show raw *args/**kwargs
    assert "--args" not in result.output
    assert "--kwargs" not in result.output


def test_dry_run_skips_write(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    tag(log_path, add=["should_persist"])
    # Verify tag was written
    reloaded = read_eval_log(log_path, header_only=True)
    assert "should_persist" in (reloaded.tags or [])

    # dry_run should not write
    tag(log_path, add=["should_not_persist"], dry_run=True)  # type: ignore[call-arg]
    reloaded = read_eval_log(log_path, header_only=True)
    assert "should_not_persist" not in (reloaded.tags or [])
    assert "should_persist" in (reloaded.tags or [])


def test_cli_step_multiple_filters(tmp_path: Path, recording_console: Console) -> None:
    filter_file = "tests/local_eval/src/local_eval/my_filters.py"

    # passes both only_success and only_anthropic
    _make_log(tmp_path, "both.eval")
    both = read_eval_log(str(tmp_path / "both.eval"))
    both = both.model_copy(
        update={"eval": both.eval.model_copy(update={"model": "anthropic/claude"})}
    )
    write_eval_log(both, str(tmp_path / "both.eval"))

    # passes only_success but not only_anthropic
    _make_log(tmp_path, "success_only.eval")

    # passes only_anthropic but not only_success
    _make_log(tmp_path, "anthropic_only.eval")
    anth = read_eval_log(str(tmp_path / "anthropic_only.eval"))
    anth = anth.model_copy(
        update={
            "status": "error",
            "eval": anth.eval.model_copy(update={"model": "anthropic/claude"}),
        }
    )
    write_eval_log(anth, str(tmp_path / "anthropic_only.eval"))

    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command,
        [
            "tag",
            str(tmp_path),
            "--add",
            "filtered",
            "--filter",
            f"{filter_file}@only_success",
            "--filter",
            f"{filter_file}@only_anthropic",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    # Verify filter summary was printed
    captured = recording_console.export_text()
    assert "only_success" in captured
    assert "2/3 logs matched" in captured
    assert "only_anthropic" in captured
    assert "1/2 logs matched" in captured

    assert "filtered" in (
        read_eval_log(str(tmp_path / "both.eval"), header_only=True).tags or []
    )
    assert "filtered" not in (
        read_eval_log(str(tmp_path / "success_only.eval"), header_only=True).tags or []
    )
    assert "filtered" not in (
        read_eval_log(str(tmp_path / "anthropic_only.eval"), header_only=True).tags
        or []
    )


def test_cli_step_exclude(tmp_path: Path, recording_console: Console) -> None:
    filter_file = "tests/local_eval/src/local_eval/my_filters.py"

    # success log (excluded by only_success)
    _make_log(tmp_path, "success.eval")

    # error log (not excluded by only_success)
    _make_log(tmp_path, "error.eval")
    error_log = read_eval_log(str(tmp_path / "error.eval"))
    error_log = error_log.model_copy(update={"status": "error"})
    write_eval_log(error_log, str(tmp_path / "error.eval"))

    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command,
        [
            "tag",
            str(tmp_path),
            "--add",
            "excluded",
            "--exclude",
            f"{filter_file}@only_success",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    captured = recording_console.export_text()
    assert "Exclude" in captured
    assert "only_success" in captured
    assert "1/2 logs remaining" in captured

    # only the error log should be tagged
    assert "excluded" not in (
        read_eval_log(str(tmp_path / "success.eval"), header_only=True).tags or []
    )
    assert "excluded" in (
        read_eval_log(str(tmp_path / "error.eval"), header_only=True).tags or []
    )


def test_cli_copy_with_store_writes_new_logs(tmp_path: Path) -> None:
    """When --store is used with copy, new log paths should be added to the store."""
    log_path = _make_log(tmp_path / "src")
    store_dir = str(tmp_path / "store")

    # Create store and import the source log
    store = DeltaLakeStore(store_path=store_dir, create=True)
    store.import_log_path(log_path)
    assert len(store.get_logs()) == 1

    dest = str(tmp_path / "dest")

    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command,
        ["copy", "--store", store_dir, "--dest", dest],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    # The copied log should exist on disk
    dest_file = tmp_path / "dest" / "test.eval"
    assert dest_file.exists()

    # The new log path should also be in the store
    store = DeltaLakeStore(store_path=store_dir)
    store_logs = store.get_logs()
    dest_paths = [log for log in store_logs if "dest" in log]
    assert len(dest_paths) == 1, f"Expected new log in store, got: {store_logs}"


def test_cli_copy_help() -> None:
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, ["copy", "--help"])
    assert result.exit_code == 0
    assert "--dest" in result.output
    assert "--source-prefix" in result.output
    assert "--args" not in result.output
    assert "--kwargs" not in result.output
