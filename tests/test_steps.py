from pathlib import Path

import pytest
from botocore.client import BaseClient
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.log import (
    EvalConfig,
    EvalDataset,
    EvalLog,
    EvalResults,
    EvalSample,
    EvalSpec,
    WriteConflictError,
    read_eval_log,
    write_eval_log,
)
from inspect_flow._steps.copy import copy
from inspect_flow._steps.run import run_step
from inspect_flow._steps.step import StepResult, step
from inspect_flow._steps.tag import metadata, tag
from inspect_flow._store.deltalake import DeltaLakeStore
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._util.error import NoLogsError
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
    [result] = tag([log_path], add=["reviewed"])
    assert "reviewed" in (result.tags or [])
    # Verify written to disk
    reloaded = read_eval_log(log_path, header_only=True)
    assert "reviewed" in (reloaded.tags or [])


def test_tag_remove_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    tag([log_path], add=["draft"])
    [result] = tag([log_path], remove=["draft"])
    assert "draft" not in (result.tags or [])
    reloaded = read_eval_log(log_path, header_only=True)
    assert "draft" not in (reloaded.tags or [])


def test_tag_from_evallog(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    log = read_eval_log(log_path)
    [result] = tag([log], add=["golden"])
    assert "golden" in (result.tags or [])


def test_tag_error_no_add_or_remove(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    with pytest.raises(ValueError, match="add.*remove"):
        tag([log_path])


def test_tag_error_empty_add_and_remove(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    with pytest.raises(ValueError, match="add.*remove"):
        tag([log_path], add=[], remove=[])


# --- metadata step ---


def test_metadata_set_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    [result] = metadata([log_path], set={"score": 0.95})
    assert result.metadata is not None
    assert result.metadata["score"] == 0.95
    reloaded = read_eval_log(log_path, header_only=True)
    assert reloaded.metadata is not None
    assert reloaded.metadata["score"] == 0.95


def test_metadata_remove_from_path(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    metadata([log_path], set={"key1": "val1", "key2": "val2"})
    [result] = metadata([log_path], remove=["key1"])
    assert result.metadata is not None
    assert "key1" not in result.metadata
    assert result.metadata["key2"] == "val2"


def test_metadata_error_no_set_or_remove(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    with pytest.raises(ValueError, match="set.*remove"):
        metadata([log_path])


def test_metadata_error_empty_set_and_remove(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    with pytest.raises(ValueError, match="set.*remove"):
        metadata([log_path], set={}, remove=[])


# --- read_log_headers ---


def test_read_log_headers_skips_missing(tmp_path: Path) -> None:
    from inspect_flow._steps.context import read_log_headers

    valid_path = _make_log(tmp_path)
    missing_path = str(tmp_path / "missing.eval")
    result = read_log_headers([valid_path, missing_path])
    assert len(result) == 1
    assert result[0].eval.task == "test_task"


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


# --- _dest_path ---


def test_dest_path_root_dest() -> None:
    from inspect_flow._steps.copy import _dest_path

    assert _dest_path("/", "sub", "test.eval") == "/sub/test.eval"
    assert _dest_path("/", "", "test.eval") == "/test.eval"


def test_dest_path_trailing_slash() -> None:
    from inspect_flow._steps.copy import _dest_path

    assert _dest_path("/a/b/", "sub", "test.eval") == "/a/b/sub/test.eval"
    assert _dest_path("/a/b", "", "test.eval") == "/a/b/test.eval"


# --- copy step ---


def test_copy_flat(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    [result] = copy([log_path], dest=dest)
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
    [result] = copy([log_path], dest=dest, source_prefix=prefix)
    assert "subdir/test.eval" in result.location


def test_copy_skips_existing(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    [first] = copy([log_path], dest=dest)
    [second] = copy([log_path], dest=dest)
    assert second.location == first.location


def test_copy_overwrite(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    [first] = copy([log_path], dest=dest)
    [second] = copy([log_path], dest=dest, overwrite=True)
    assert second.location == first.location


def test_copy_with_suffix(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    [result] = copy([log_path], dest=dest, suffix="+realigned")
    assert Path(result.location).name == "test+realigned.eval"
    reloaded = read_eval_log(result.location)
    assert reloaded.eval.task == "test_task"
    assert Path(log_path).exists()


def test_copy_with_rename(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    [result] = copy([log_path], dest=dest, rename=lambda name: f"renamed-{name}")
    assert Path(result.location).name == "renamed-test.eval"
    reloaded = read_eval_log(result.location)
    assert reloaded.eval.task == "test_task"


def test_copy_suffix_with_source_prefix(tmp_path: Path) -> None:
    src_dir = tmp_path / "src" / "subdir"
    src_dir.mkdir(parents=True)
    log_path = _make_log(src_dir)
    dest = str(tmp_path / "dest")
    prefix = str(tmp_path / "src")
    [result] = copy([log_path], dest=dest, source_prefix=prefix, suffix="+v2")
    assert result.location.endswith("subdir/test+v2.eval")
    assert Path(result.location).exists()


def test_copy_error_suffix_and_rename(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    with pytest.raises(ValueError, match="suffix.*rename"):
        copy([log_path], dest=str(tmp_path / "dest"), suffix="+a", rename=lambda n: n)


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
    [log] = tag([log], add=["golden"], reason="Promoted")
    [log] = copy([log], dest=dest)
    # Destination log has the tag
    reloaded = read_eval_log(log.location)
    assert "golden" in (reloaded.tags or [])


# --- @step with deferred writes (design doc example) ---


def test_nested_step_defers_writes(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def promote(logs: list[EvalLog], *, dest: str) -> list[EvalLog]:
        logs = tag(logs, add=["golden"], reason="Promoted")
        return copy(logs, dest=dest)

    dest = str(tmp_path / "dest")
    [result] = promote([log_path], dest=dest)
    # Source was written with tag
    reloaded_src = read_eval_log(log_path, header_only=True)
    assert "golden" in (reloaded_src.tags or [])
    # Destination was written
    reloaded_dest = read_eval_log(result.location)
    assert "golden" in (reloaded_dest.tags or [])
    assert reloaded_dest.samples is not None
    assert len(reloaded_dest.samples) == 1


# --- run_step across multiple logs ---


def test_run_step_no_logs(tmp_path: Path) -> None:
    with pytest.raises(NoLogsError, match="No logs found"):
        run_step(tag, str(tmp_path), add=["batch"])


def test_run_step_filter_preserves_in_memory_evallog(tmp_path: Path) -> None:
    """run_step with filter= must pass the original in-memory EvalLog to the step.

    Regression: filtering converted survivors back to log.location strings,
    so the step re-read from disk and lost in-memory mutations.
    """
    log_path = _make_log(tmp_path)
    log = read_eval_log(log_path)
    # Mutate in memory only — add a tag that the on-disk version doesn't have.
    log = log.model_copy(update={"tags": ["in_memory"]})

    seen_tags: list[list[str]] = []

    @step
    def capture(logs: list[EvalLog]) -> list[EvalLog]:
        for log in logs:
            seen_tags.append(list(log.tags or []))
        return logs

    # Filter matches the in-memory object (status == "success").
    run_step(
        capture,
        [log],
        filter="tests/local_eval/src/local_eval/my_filters.py@only_success",
    )
    assert len(seen_tags) == 1
    assert "in_memory" in seen_tags[0], (
        f"step received disk version instead of in-memory EvalLog, tags={seen_tags[0]}"
    )


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
    def check_no_samples(logs: list[EvalLog]) -> list[EvalLog]:
        for log in logs:
            assert log.samples is None
        return logs

    check_no_samples([log_path])


# --- samples preserved after header_only step writes back ---


def test_header_only_step_preserves_samples_on_write(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)
    tag([log_path], add=["test"])
    reloaded = read_eval_log(log_path)
    assert reloaded.samples is not None
    assert len(reloaded.samples) == 1


def test_nested_header_only_step_preserves_samples(tmp_path: Path) -> None:
    """A header_only step that calls another header_only step (e.g. tag)
    must not destroy samples on disk."""
    log_path = _make_log(tmp_path)

    @step
    def qa(logs: list[EvalLog]) -> list[EvalLog]:
        return tag(logs, add=["qa_passed"])

    qa([log_path])
    reloaded = read_eval_log(log_path)
    assert "qa_passed" in (reloaded.tags or [])
    assert reloaded.samples is not None
    assert len(reloaded.samples) == 1


# --- StepResult ---


def test_step_result_skip_log_steps(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def skip_step(logs: list[EvalLog]) -> StepResult:
        return StepResult(logs=logs, skip_log_steps=True)

    result = skip_step([log_path])
    assert result == []


def test_step_result_modified_false_does_not_advance_context(tmp_path: Path) -> None:
    """StepResult(modified=False) must not advance context.log.

    A nested step returning modified=False should not become the current log
    for subsequent nested steps — the original log should remain current.
    """
    log_path = _make_log(tmp_path)

    @step
    def read_then_tag(logs: list[EvalLog]) -> list[EvalLog]:
        # Nested step that returns modified=False with a mutated log
        @step
        def read_only(logs: list[EvalLog]) -> StepResult:
            modified_logs = [log.model_copy(update={"status": "error"}) for log in logs]
            return StepResult(logs=modified_logs, modified=False)

        read_only(logs)
        # tag should run against the original logs, not the read_only result
        return tag(logs, add=["after_read_only"])

    read_then_tag([log_path])
    reloaded = read_eval_log(log_path, header_only=True)
    assert "after_read_only" in (reloaded.tags or [])
    # The read_only step's status change should NOT have been written
    assert reloaded.status == "success"


def test_step_result_modified_false_does_not_write(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def read_only_step(logs: list[EvalLog]) -> StepResult:
        return StepResult(logs=logs, modified=False)

    [result] = read_only_step([log_path])
    # Log should not have been modified on disk — no tags added
    reloaded = read_eval_log(log_path, header_only=True)
    assert not reloaded.tags


def test_return_none_skips(tmp_path: Path) -> None:
    log_path = _make_log(tmp_path)

    @step
    def none_step(logs: list[EvalLog]) -> list[EvalLog]:
        return []

    result = none_step([log_path])
    assert result == []


# --- nested step receives path raises ---


# --- _format_step_call ---


def _tag_stub() -> None: ...


def _qa_stub() -> None: ...


def test_format_step_call_basic() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert (
        _format_step_call(_tag_stub, 3, {"add": ["golden"]})
        == "_tag_stub(logs=3, add=['golden'])"
    )


def test_format_step_call_hides_none() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert (
        _format_step_call(_tag_stub, 1, {"add": ["golden"], "remove": None})
        == "_tag_stub(logs=1, add=['golden'])"
    )


def test_format_step_call_hides_empty_sequences() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert (
        _format_step_call(_tag_stub, 2, {"add": ["golden"], "remove": []})
        == "_tag_stub(logs=2, add=['golden'])"
    )
    assert (
        _format_step_call(_tag_stub, 2, {"add": ["golden"], "remove": ()})
        == "_tag_stub(logs=2, add=['golden'])"
    )


def test_format_step_call_converts_tuples_to_lists() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert (
        _format_step_call(_tag_stub, 1, {"add": ("tag1",)})
        == "_tag_stub(logs=1, add=['tag1'])"
    )


def test_format_step_call_no_args() -> None:
    from inspect_flow._steps.step import _format_step_call

    assert _format_step_call(_qa_stub, 5, {}) == "_qa_stub(logs=5)"


def test_format_step_call_hides_signature_defaults() -> None:
    """kwargs whose value matches the function's signature default are hidden."""
    from inspect_flow._steps.step import _format_step_call

    def myop(logs: list[EvalLog], debug: bool = False, port: int = 5678) -> None: ...

    assert _format_step_call(myop, 1, {"debug": False, "port": 5678}) == "myop(logs=1)"
    assert (
        _format_step_call(myop, 1, {"debug": True, "port": 5678})
        == "myop(logs=1, debug=True)"
    )


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
    assert reloaded.metadata["score_threshold"] == 0.9


def test_cli_metadata_set_dict_value(tmp_path: Path) -> None:
    """Values that are valid JSON should be parsed, not stored as strings."""
    log_path = _make_log(tmp_path)

    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command,
        ["metadata", log_path, "--set", 'a={"a": {"a": "a"}}'],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    reloaded = read_eval_log(log_path, header_only=True)
    assert reloaded.metadata is not None
    assert reloaded.metadata["a"] == {"a": {"a": "a"}}


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
    tag([log_path], add=["should_persist"])
    # Verify tag was written
    reloaded = read_eval_log(log_path, header_only=True)
    assert "should_persist" in (reloaded.tags or [])

    # dry_run should not write
    tag([log_path], add=["should_not_persist"], dry_run=True)  # type: ignore[call-arg]
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


def test_copy_with_store_writes_new_logs(tmp_path: Path) -> None:
    """When store= is passed to copy directly, new log paths are added to the store."""
    log_path = _make_log(tmp_path / "src")
    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True)
    store.import_log_path(log_path)

    dest = str(tmp_path / "dest")
    [result] = copy([log_path], dest=dest, store=store)

    store = DeltaLakeStore(store_path=store_dir)
    store_logs = store.get_logs()
    assert any("dest" in log for log in store_logs), (
        f"Expected new log in store, got: {store_logs}"
    )


def test_copy_with_store_path_writes_new_logs(tmp_path: Path) -> None:
    """When store= is a string path, copy resolves it and adds new logs."""
    log_path = _make_log(tmp_path / "src")
    store_dir = str(tmp_path / "store")

    dest = str(tmp_path / "dest")
    [result] = copy([log_path], dest=dest, store=store_dir)

    store = store_factory(store_dir, base_dir=str(tmp_path), quiet=True)
    assert store is not None
    store_logs = store.get_logs()
    assert any("dest" in log for log in store_logs), (
        f"Expected new log in store, got: {store_logs}"
    )


def test_copy_and_change_task_args_adds_new_store_identifier(tmp_path: Path) -> None:
    """Reference: copy a log and change its args so it becomes a *distinct* task
    in the store.

    The store keys logs by `task_identifier`, which hashes `task_args_passed`
    (not `task_args`). A step that copies a log and updates *both* arg dicts
    therefore produces a new file under a new identifier, leaving the original
    entry intact — so the store holds two entries with different identifiers.
    """
    from inspect_flow._store.deltalake import LOGS, _task_id_col

    log_path = _make_log(tmp_path / "src")
    store_dir = str(tmp_path / "store")
    store = DeltaLakeStore(store_path=store_dir, create=True)
    store.import_log_path(log_path)

    dest = str(tmp_path / "dest")

    @step
    def copy_and_align_task_args(
        logs: list[EvalLog],
        *,
        dest: str,
        args: dict[str, object],
        store: FlowStore | str | None = None,  # noqa: ARG001 handled by @step wrapper
    ) -> list[EvalLog]:
        copied = copy(logs, dest=dest)
        modified_logs = []
        for log in copied:
            new_eval = log.eval.model_copy(
                update={
                    "task_args": {**log.eval.task_args, **args},
                    "task_args_passed": {**log.eval.task_args_passed, **args},
                }
            )
            modified_logs.append(log.model_copy(update={"eval": new_eval}))
        return modified_logs

    copy_and_align_task_args(
        [log_path], dest=dest, args={"temperature": 0.5}, store=store
    )

    store = DeltaLakeStore(store_path=store_dir)
    table = (
        store._open_table(LOGS)
        .to_pyarrow_dataset()
        .to_table(columns=[_task_id_col(), "log_path"])
    )
    by_path = dict(
        zip(
            table["log_path"].to_pylist(),
            table[_task_id_col()].to_pylist(),
            strict=True,
        )
    )

    src_id = next(tid for p, tid in by_path.items() if "src" in p)
    dest_id = next(tid for p, tid in by_path.items() if "dest" in p)
    assert len(by_path) == 2
    assert src_id != dest_id


def test_nested_tag_with_same_path_preserves_both_tags(tmp_path: Path) -> None:
    """Nested steps called with log.location must see prior dirty mutations.

    Regression: when an outer step calls tag(log.location, add=["a"]) then
    tag(log.location, add=["b"]), context.log was never advanced to the dirty
    version, so the second tag replayed from stale state and only "b" survived.
    """
    log_path = _make_log(tmp_path)

    @step
    def add_two_tags(logs: list[EvalLog]) -> list[EvalLog]:
        logs = tag(logs, add=["a"])
        logs = tag(logs, add=["b"])
        return logs

    add_two_tags([log_path])
    reloaded = read_eval_log(log_path, header_only=True)
    assert "a" in (reloaded.tags or []), f"tag 'a' missing, tags={reloaded.tags}"
    assert "b" in (reloaded.tags or []), f"tag 'b' missing, tags={reloaded.tags}"


def test_cli_copy_help() -> None:
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, ["copy", "--help"])
    assert result.exit_code == 0
    assert "--dest" in result.output
    assert "--source-prefix" in result.output
    assert "--suffix" in result.output
    assert "--rename" not in result.output
    assert "--args" not in result.output
    assert "--kwargs" not in result.output


def test_cli_copy_suffix_run(tmp_path: Path) -> None:
    """flow step copy PATH --dest DEST --suffix SUFFIX copies with the suffix."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    log_path = _make_log(tmp_path / "src")
    dest = str(tmp_path / "dest")
    result = CliRunner().invoke(
        step_command, ["copy", log_path, "--dest", dest, "--suffix", "+realigned"]
    )
    assert result.exit_code == 0
    reloaded = read_eval_log(str(tmp_path / "dest" / "test+realigned.eval"))
    assert reloaded.eval.task == "test_task"


# --- etag concurrency guard ---


def test_write_dirty_uses_etag_guard(mock_s3: BaseClient) -> None:
    """write_dirty must pass if_match_etag so concurrent writes are detected.

    Writes a log to S3, reads it (capturing etag), mutates it behind the
    step's back, then verifies that write_dirty raises WriteConflictError.
    """
    from inspect_ai.log import ProvenanceData, TagsEdit, edit_eval_log

    s3_path = "s3://test-bucket/etag_test.eval"
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
    )
    write_eval_log(log, s3_path)

    # Read back — this captures the etag from S3
    log_with_etag = read_eval_log(s3_path, header_only=True)
    assert log_with_etag.etag is not None

    # Simulate concurrent modification via edit_eval_log (produces a real
    # log_updates entry that changes the on-disk content and thus the S3 etag)
    concurrent_log = read_eval_log(s3_path, header_only=True)
    concurrent_log = edit_eval_log(
        concurrent_log,
        [TagsEdit(tags_add=["concurrent"], tags_remove=[])],
        ProvenanceData(author="other-user"),
    )
    write_eval_log(concurrent_log, s3_path)

    # Now tag the stale log — write_dirty should detect the conflict
    with pytest.raises(WriteConflictError):
        tag([log_with_etag], add=["should_conflict"])


def test_copy_to_s3_does_not_use_source_etag(mock_s3: BaseClient) -> None:
    """copy must not pass the source log's etag when writing to a new destination.

    Regression: the generic etag guard passed if_match_etag for every dirty
    write, but copy changes location — the destination is a new object with no
    prior etag. Passing the source's etag causes a spurious PreconditionFailed.
    """
    src_path = "s3://test-bucket/src/test.eval"
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
        samples=[
            EvalSample(id=1, epoch=1, input="hello", target="world", uuid="uuid-1"),
        ],
    )
    write_eval_log(log, src_path)

    # Read back from S3 — this captures the source etag
    src_log = read_eval_log(src_path)
    assert src_log.etag is not None

    # Copy to a new S3 path — should succeed, not fail with WriteConflictError
    dest = "s3://test-bucket/dest"
    [result] = copy([src_log], dest=dest)

    # Verify the copy landed
    copied = read_eval_log(result.location)
    assert copied.eval.task == "test_task"


# --- file-based step loading ---

FILE_STEP_PATH = str(Path(__file__).parent / "config" / "file_step.py")


def test_cli_file_step_group_help() -> None:
    """flow step file.py --help lists steps from that file."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, [FILE_STEP_PATH, "--help"])
    assert result.exit_code == 0
    assert "file_step_a" in result.output
    assert "file_step_b" in result.output


def test_cli_file_step_subcommand_help() -> None:
    """flow step file.py step_name --help shows that step's options.

    file_step.py uses `from __future__ import annotations`, so this also
    verifies that stringized annotations are resolved: --label keeps its str
    type and the callable --transform param is excluded from the CLI.
    """
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, [FILE_STEP_PATH, "file_step_a", "--help"])
    assert result.exit_code == 0
    assert "--label" in result.output
    assert "--transform" not in result.output


def test_cli_file_step_at_syntax_help() -> None:
    """flow step file.py@step_name --help shows that step's options."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command, [f"{FILE_STEP_PATH}@file_step_a", "--help"]
    )
    assert result.exit_code == 0
    assert "--label" in result.output


def test_cli_file_step_run(tmp_path: Path) -> None:
    """flow step file.py step_name PATH runs the step."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    log_path = _make_log(tmp_path)
    result = CliRunner().invoke(
        step_command, [FILE_STEP_PATH, "file_step_a", "--label", "hello", log_path]
    )
    assert result.exit_code == 0
    reloaded = read_eval_log(log_path, header_only=True)
    assert "hello" in (reloaded.tags or [])


def test_cli_file_step_type_checking_annotations() -> None:
    """Steps with annotation imports guarded by TYPE_CHECKING still get a CLI.

    eval_str annotation resolution raises NameError for such files; the CLI
    falls back to the unevaluated signature instead of crashing.
    """
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    type_checking_path = str(
        Path(__file__).parent / "config" / "file_step_type_checking.py"
    )
    result = CliRunner().invoke(
        step_command, [type_checking_path, "type_checking", "--help"]
    )
    assert result.exit_code == 0
    assert "--label" in result.output


def test_cli_file_step_required_callable_errors() -> None:
    """A step with a required Python-only param fails with a usage error.

    The callable param can't be expressed on the CLI, so invoking the step
    reports a clear error instead of crashing with a TypeError.
    """
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(
        step_command, [FILE_STEP_PATH, "file_step_required_callable", "some.eval"]
    )
    assert result.exit_code == 2
    assert "Python-only parameter(s) (transform)" in result.output


def test_cli_file_step_optional_list_option(tmp_path: Path) -> None:
    """An Optional[list[str]] param maps to a repeatable CLI option."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    log_path = _make_log(tmp_path)
    result = CliRunner().invoke(
        step_command,
        [FILE_STEP_PATH, "file_step_b", "--labels", "a", "--labels", "b", log_path],
    )
    assert result.exit_code == 0
    reloaded = read_eval_log(log_path, header_only=True)
    assert {"a", "b"} <= set(reloaded.tags or [])


def test_cli_file_step_at_syntax_run(tmp_path: Path) -> None:
    """flow step file.py@step_name PATH runs the step."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    log_path = _make_log(tmp_path)
    result = CliRunner().invoke(
        step_command,
        [f"{FILE_STEP_PATH}@file_step_a", "--label", "world", log_path],
    )
    assert result.exit_code == 0
    reloaded = read_eval_log(log_path, header_only=True)
    assert "world" in (reloaded.tags or [])


# --- scan step ---


def test_scan_default_scans_dir_under_log_dir(tmp_path: Path) -> None:
    """When scans is None, it defaults to <log_dir>/scans where log_dir is
    the common directory of all input log locations."""
    from unittest.mock import patch

    from inspect_flow._steps.scan import scan

    log1 = read_eval_log(_make_log(tmp_path, "log1.eval"))
    log2 = read_eval_log(_make_log(tmp_path, "log2.eval"))

    with patch("inspect_flow._steps.scan.scout_scan") as mock:
        scan([log1, log2], scanners=[])

    assert mock.call_args.kwargs["scans"] == str(tmp_path / "scans")


def test_scan_default_scans_errors_on_mixed_dirs(tmp_path: Path) -> None:
    """When scans is None and logs are in different directories, raise."""
    from inspect_flow._steps.scan import scan

    dir1 = tmp_path / "a"
    dir2 = tmp_path / "b"
    dir1.mkdir()
    dir2.mkdir()
    log1 = read_eval_log(_make_log(dir1, "log.eval"))
    log2 = read_eval_log(_make_log(dir2, "log.eval"))

    with pytest.raises(ValueError, match="multiple directories"):
        scan([log1, log2], scanners=[])


def test_scan_writes_scout_project_file(tmp_path: Path) -> None:
    """`scan` writes a scout.yaml in the parent of the scans dir with
    `transcripts` set to the log dir and `scans` set to the scans dir."""
    from unittest.mock import patch

    import yaml
    from inspect_flow._steps.scan import scan

    log = read_eval_log(_make_log(tmp_path))
    scans_dir = str(tmp_path / "out" / "scans")

    with patch("inspect_flow._steps.scan.scout_scan"):
        scan([log], scanners=[], scans=scans_dir)

    project_file = tmp_path / "out" / "scout.yaml"
    assert project_file.exists()
    project = yaml.safe_load(project_file.read_text())
    assert project == {"transcripts": str(tmp_path), "scans": scans_dir}


def test_scan_writes_scout_project_file_for_bare_scans_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When scans is a bare relative path (no parent dir, e.g. 'scan_dir'),
    it should be resolved to an absolute path under the current working
    directory before being written to scout.yaml."""
    from unittest.mock import patch

    import yaml
    from inspect_flow._steps.scan import scan

    log = read_eval_log(_make_log(tmp_path))
    monkeypatch.chdir(tmp_path)

    with patch("inspect_flow._steps.scan.scout_scan"):
        scan([log], scanners=[], scans="scan_dir")

    project_file = tmp_path / "scout.yaml"
    assert project_file.exists()
    project = yaml.safe_load(project_file.read_text())
    assert project == {
        "transcripts": str(tmp_path),
        "scans": str(tmp_path / "scan_dir"),
    }


def test_scan_preserves_existing_scout_project_file(tmp_path: Path) -> None:
    """If a scout.yaml already exists, `scan` leaves it unchanged."""
    from unittest.mock import patch

    from inspect_flow._steps.scan import scan

    log = read_eval_log(_make_log(tmp_path))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    scans_dir = str(out_dir / "scans")
    project_file = out_dir / "scout.yaml"
    original = "filter: model = 'gpt-4'\n"
    project_file.write_text(original)

    with patch("inspect_flow._steps.scan.scout_scan"):
        scan([log], scanners=[], scans=scans_dir)

    assert project_file.read_text() == original


def test_scan_scout_project_paths_consistent_when_location_is_file_uri(
    tmp_path: Path,
) -> None:
    """scout.yaml paths should be plain absolute (no file://) regardless of
    whether log.location includes a file:// prefix (e.g. when logs came via
    list_eval_logs)."""
    from unittest.mock import patch

    import yaml
    from inspect_ai.log import list_eval_logs
    from inspect_flow._steps.scan import scan

    _make_log(tmp_path)
    # list_eval_logs returns names with file:// prefix on local filesystems
    infos = list_eval_logs(str(tmp_path))
    log = read_eval_log(infos[0].name)
    assert log.location.startswith("file://")

    scans_dir = str(tmp_path / "out" / "scans")
    with patch("inspect_flow._steps.scan.scout_scan") as mock:
        scan([log], scanners=[], scans=scans_dir)

    project_file = tmp_path / "out" / "scout.yaml"
    assert project_file.exists()
    project = yaml.safe_load(project_file.read_text())
    assert project == {"transcripts": str(tmp_path), "scans": scans_dir}
    assert mock.call_args.kwargs["scans"] == scans_dir


def test_scan_default_scans_absolute_when_location_is_file_uri(
    tmp_path: Path,
) -> None:
    """When scans is None and log.location has file:// prefix, the inferred
    scans path should be a plain absolute path (no file://)."""
    from unittest.mock import patch

    import yaml
    from inspect_ai.log import list_eval_logs
    from inspect_flow._steps.scan import scan

    _make_log(tmp_path)
    infos = list_eval_logs(str(tmp_path))
    log = read_eval_log(infos[0].name)

    with patch("inspect_flow._steps.scan.scout_scan") as mock:
        scan([log], scanners=[])

    expected_scans = str(tmp_path / "scans")
    assert mock.call_args.kwargs["scans"] == expected_scans
    project_file = tmp_path / "scout.yaml"
    project = yaml.safe_load(project_file.read_text())
    assert project == {"transcripts": str(tmp_path), "scans": expected_scans}


def test_scan_validation_actionable_error_on_scout_import_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When inspect_scout._cli is unimportable (scout/inspect-ai version skew),
    scan(validation=...) raises an actionable error instead of a raw ImportError."""
    import sys

    from inspect_flow._steps.scan import scan

    log = read_eval_log(_make_log(tmp_path))
    # Setting a sys.modules entry to None makes its import raise ImportError,
    # simulating the version skew regardless of the installed scout version.
    monkeypatch.setitem(sys.modules, "inspect_scout._cli.scan", None)

    with pytest.raises(PrerequisiteError, match=r"upgrade inspect-scout"):
        scan([log], scanners=[], validation=("validation.yaml",))


def test_cli_scan_help_describes_default_scans() -> None:
    """`flow step scan --help` documents the inferred --scans default."""
    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    result = CliRunner().invoke(step_command, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--scans" in result.output
    assert "alongside the input logs" in result.output


def test_cli_scan_only_prints_user_provided_params(
    tmp_path: Path, recording_console: Console
) -> None:
    """`flow step scan` should only show params the user passed on the CLI.

    Regression: defaults like shuffle=0, debug=False, debug_port=5678,
    fail_on_error=False were being rendered in the scan(...) call summary
    even when the user didn't pass those flags.
    """
    from unittest.mock import patch

    from click.testing import CliRunner
    from inspect_flow._cli.step import step_command

    log_path = _make_log(tmp_path)

    with patch("inspect_flow._steps.scan.scan") as mock_scan:
        result = CliRunner().invoke(
            step_command,
            [
                "scan",
                log_path,
                "--scanners",
                "fake/scanner.py",
                "--model",
                "openai/gpt-5-nano",
                "--dry-run",
            ],
            catch_exceptions=False,
        )
    assert result.exit_code == 0, result.output
    assert mock_scan.called

    captured = recording_console.export_text()
    assert "scan(" in captured
    assert "scanners='fake/scanner.py'" in captured
    assert "model='openai/gpt-5-nano'" in captured
    # Defaults the user didn't set must not appear
    assert "shuffle=" not in captured
    assert "debug=" not in captured
    assert "debug_port=" not in captured
    assert "fail_on_error=" not in captured
