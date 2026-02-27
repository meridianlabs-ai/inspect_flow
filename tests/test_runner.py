import sys
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner
from inspect_ai import Epochs, Task, task_with
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalResults, EvalSpec
from inspect_ai.model import Model, get_model
from inspect_flow._display.display import set_display, set_display_type
from inspect_flow._runner.cli import _read_config, flow_run
from inspect_flow._runner.logs import (
    _epochs_reducer_changed,
    _num_samples,
    find_existing_logs,
    num_log_samples,
)
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.run import (
    _bundle_url_output,
    _fix_prerequisite_error_message,
    _option_string,
)
from inspect_flow._runner.task_log import (
    TaskLogInfo,
    _unique_task_names,
    create_task_log_display,
)
from inspect_flow._types.flow_types import FlowOptions, FlowSpec, not_given
from rich.console import Console


def _render_text(renderable: object, width: int = 80) -> str:
    c = Console(width=width, no_color=True, highlight=False)
    with c.capture() as capture:
        c.print(renderable)
    return capture.get()


def _make_task(
    name: str = "task",
    num_samples: int = 3,
    model: str | Model | None = None,
    epochs: int | Epochs | None = None,
) -> Task:
    samples = [Sample(input=f"sample_{i}") for i in range(num_samples)]
    return Task(
        dataset=MemoryDataset(samples=samples),
        name=name,
        model=model,
        epochs=epochs,
    )


def _make_eval_log(
    results: EvalResults | None = None,
    invalidated: bool = False,
    epochs: int | None = None,
    epochs_reducer: list[str] | None = None,
) -> EvalLog:
    config = EvalConfig(epochs=epochs, epochs_reducer=epochs_reducer)
    return EvalLog(
        status="success",
        eval=EvalSpec(
            created="2024-01-01T00:00:00Z",
            task="task",
            dataset=EvalDataset(),
            model="none",
            config=config,
        ),
        results=results,
        invalidated=invalidated,
    )


# ── resolve.py ──────────────────────────────────────────────


class TestResolveSpec:
    def test_clears_defaults_and_sets_python_version(self) -> None:
        spec = FlowSpec(
            tasks=["my_task"],
            log_dir="./logs",
            defaults=None,
        )
        resolved = resolve_spec(spec, base_dir=".")
        assert resolved.defaults == not_given
        expected_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert resolved.python_version == expected_version

    def test_preserves_other_fields(self) -> None:
        spec = FlowSpec(tasks=["my_task"], log_dir="./logs")
        resolved = resolve_spec(spec, base_dir=".")
        assert resolved.tasks
        assert len(list(resolved.tasks)) == 1
        assert resolved.log_dir == "./logs"


# ── logs.py ─────────────────────────────────────────────────


class TestNumSamples:
    def test_no_limit(self) -> None:
        task = _make_task(num_samples=5)
        assert _num_samples(task, None) == 5

    def test_int_limit_less_than_count(self) -> None:
        task = _make_task(num_samples=5)
        assert _num_samples(task, 3) == 3

    def test_int_limit_greater_than_count(self) -> None:
        task = _make_task(num_samples=5)
        assert _num_samples(task, 10) == 5

    def test_tuple_limit(self) -> None:
        task = _make_task(num_samples=10)
        assert _num_samples(task, (2, 5)) == 3

    def test_tuple_start_ge_count(self) -> None:
        task = _make_task(num_samples=3)
        assert _num_samples(task, (3, 10)) == 0

    def test_epochs_multiplier(self) -> None:
        task = _make_task(num_samples=4, epochs=Epochs(3))
        assert _num_samples(task, None) == 12

    def test_epochs_with_limit(self) -> None:
        task = _make_task(num_samples=10, epochs=Epochs(2))
        assert _num_samples(task, 5) == 10


class TestEpochsReducerChanged:
    def test_none_epochs_not_changed(self) -> None:
        assert _epochs_reducer_changed(None, EvalConfig()) is False

    def test_matching_default_reducer(self) -> None:
        epochs = Epochs(2, reducer=None)
        config = EvalConfig(epochs_reducer=["mean"])
        assert _epochs_reducer_changed(epochs, config) is False

    def test_matching_explicit_reducer(self) -> None:
        epochs = Epochs(2, reducer="mean")
        config = EvalConfig(epochs_reducer=["mean"])
        assert _epochs_reducer_changed(epochs, config) is False

    def test_mismatched_reducer(self) -> None:
        epochs = Epochs(2, reducer="max")
        config = EvalConfig(epochs_reducer=["mean"])
        assert _epochs_reducer_changed(epochs, config) is True

    def test_none_reducer_vs_non_default(self) -> None:
        epochs = Epochs(2, reducer=None)
        config = EvalConfig(epochs_reducer=["max"])
        assert _epochs_reducer_changed(epochs, config) is True


class TestNumLogSamples:
    def test_no_results(self) -> None:
        header = _make_eval_log(results=None)
        info = TaskLogInfo(task=_make_task(), task_samples=3)
        assert num_log_samples(header, info, None) == 0

    def test_invalidated(self) -> None:
        header = _make_eval_log(
            results=EvalResults(completed_samples=3),
            invalidated=True,
        )
        info = TaskLogInfo(task=_make_task(), task_samples=3)
        assert num_log_samples(header, info, None) == 0

    def test_reducer_changed(self) -> None:
        header = _make_eval_log(
            results=EvalResults(completed_samples=6),
            epochs=2,
            epochs_reducer=["mean"],
        )
        task = task_with(_make_task(), epochs=Epochs(2, reducer="max"))
        info = TaskLogInfo(task=task)
        assert num_log_samples(header, info, None) == 0

    def test_matching_reducer(self) -> None:
        header = _make_eval_log(
            results=EvalResults(completed_samples=6),
            epochs=2,
            epochs_reducer=["max"],
        )
        task = task_with(_make_task(), epochs=Epochs(2, reducer="max"))
        info = TaskLogInfo(task=task)
        assert num_log_samples(header, info, None) == 6

    def test_log_epoch_count_le_epoch_count(self) -> None:
        header = _make_eval_log(
            results=EvalResults(completed_samples=6),
            epochs=1,
        )
        info = TaskLogInfo(task=_make_task(epochs=Epochs(2)))
        assert num_log_samples(header, info, None) == 6

    def test_log_epoch_count_gt_epoch_count(self) -> None:
        header = _make_eval_log(
            results=EvalResults(completed_samples=12),
            epochs=4,
        )
        info = TaskLogInfo(task=_make_task(epochs=Epochs(2)))
        assert num_log_samples(header, info, None) == 6


class TestFindExistingLogs:
    @patch("inspect_flow._runner.logs.list_all_eval_logs")
    def test_unexpected_log_raises_prerequisite_error(
        self, mock_list_logs: MagicMock, recording_console: Console
    ) -> None:
        unrecognized_log = MagicMock()
        unrecognized_log.task_identifier = "unknown_task_id"
        unrecognized_log.info.name = "/logs/unexpected.eval"
        mock_list_logs.return_value = [unrecognized_log]

        spec = FlowSpec(tasks=["t"], log_dir="./logs")
        with pytest.raises(PrerequisiteError, match="not associated with a task"):
            find_existing_logs(task_id_to_task={}, spec=spec, store=None)

    @patch("inspect_flow._runner.logs.list_all_eval_logs")
    def test_unexpected_log_allowed_when_dirty(
        self, mock_list_logs: MagicMock, recording_console: Console
    ) -> None:
        unrecognized_log = MagicMock()
        unrecognized_log.task_identifier = "unknown_task_id"
        mock_list_logs.return_value = [unrecognized_log]

        spec = FlowSpec(
            tasks=["t"],
            log_dir="./logs",
            options=FlowOptions(log_dir_allow_dirty=True),
        )
        result = find_existing_logs(task_id_to_task={}, spec=spec, store=None)
        assert result == {}


# ── task_log.py ─────────────────────────────────────────────


class TestUniqueTaskNames:
    def test_single_task_no_qualifiers(self) -> None:
        infos = [TaskLogInfo(task=_make_task("alpha"))]
        result = _unique_task_names(infos)
        assert result.names[0][0] == "alpha"
        assert result.names[0][1].plain == ""

    def test_same_name_different_models(self) -> None:
        t1 = _make_task("t", model=get_model("mockllm/model-a"))
        t2 = _make_task("t", model=get_model("mockllm/model-b"))
        infos = [TaskLogInfo(task=t1), TaskLogInfo(task=t2)]
        result = _unique_task_names(infos)
        assert "mockllm/model-a" in result.names[0][1].plain
        assert "mockllm/model-b" in result.names[1][1].plain
        assert result.model_only is True

    def test_same_name_same_model_different_args(self) -> None:
        model = get_model("mockllm/model-a")
        t1 = _make_task("t", model=model)
        t2 = _make_task("t", model=model)
        infos = [
            TaskLogInfo(task=t1, flow_task=MagicMock(args={"temp": "high"})),
            TaskLogInfo(task=t2, flow_task=MagicMock(args={"temp": "low"})),
        ]
        result = _unique_task_names(infos)
        assert result.model_only is False
        assert "high" in result.names[0][1].plain
        assert "low" in result.names[1][1].plain


class TestCreateTaskLogDisplay:
    def test_running_no_complete(self) -> None:
        info = {
            "id1": TaskLogInfo(task=_make_task("alpha"), task_samples=3, log_samples=0),
        }
        output = _render_text(create_task_log_display(info, completed=False))
        assert "Running" in output
        assert "1" in output
        assert "alpha" in output

    def test_running_some_complete(self) -> None:
        info = {
            "id1": TaskLogInfo(task=_make_task("a"), task_samples=3, log_samples=3),
            "id2": TaskLogInfo(task=_make_task("b"), task_samples=5, log_samples=0),
        }
        output = _render_text(create_task_log_display(info, completed=False))
        assert "Running" in output
        assert "1 task complete" in output

    def test_completed_all(self) -> None:
        info = {
            "id1": TaskLogInfo(task=_make_task("a"), task_samples=3, log_samples=3),
            "id2": TaskLogInfo(task=_make_task("b"), task_samples=5, log_samples=5),
        }
        output = _render_text(create_task_log_display(info, completed=True))
        assert "Completed" in output
        assert "2 tasks" in output

    def test_completed_partial(self) -> None:
        info = {
            "id1": TaskLogInfo(task=_make_task("a"), task_samples=3, log_samples=3),
            "id2": TaskLogInfo(task=_make_task("b"), task_samples=5, log_samples=0),
        }
        output = _render_text(create_task_log_display(info, completed=True))
        assert "Completed" in output
        assert "1 of 2" in output

    def test_table_shows_samples(self) -> None:
        info = {
            "id1": TaskLogInfo(
                task=_make_task("x"),
                task_samples=10,
                log_samples=5,
                log_file="/tmp/log.json",
            ),
        }
        output = _render_text(create_task_log_display(info, completed=False))
        assert "5/10" in output
        assert "x" in output


# ── run.py ──────────────────────────────────────────────────


class TestOptionString:
    def test_empty_options(self) -> None:
        assert _option_string(FlowOptions()) is None

    def test_options_with_fields_set(self) -> None:
        opts = FlowOptions(max_tasks=5, score=False)
        result = _option_string(opts)
        assert result is not None
        assert "max_tasks" in result
        assert "score" in result


class TestFixPrerequisiteErrorMessage:
    def test_replaces_overwrite(self) -> None:
        e = PrerequisiteError("Use 'overwrite' to continue")
        _fix_prerequisite_error_message(e)
        assert "'bundle_overwrite'" in str(e.message)
        assert "'bundle_overwrite'" in str(e.args[0])

    def test_no_overwrite_unchanged(self) -> None:
        e = PrerequisiteError("Some other error")
        _fix_prerequisite_error_message(e)
        assert str(e.message) == "Some other error"
        assert str(e.args[0]) == "Some other error"


class TestBundleUrlOutput:
    def test_no_bundle_dir(self) -> None:
        spec = FlowSpec(tasks=["t"], log_dir="./logs")
        assert _bundle_url_output(spec) is None

    def test_bundle_dir_with_matching_mapping(self) -> None:
        spec = FlowSpec(
            tasks=["t"],
            log_dir="./logs",
            options=FlowOptions(
                bundle_dir="/local/bundles",
                bundle_url_mappings={"/local": "https://example.com"},
            ),
        )
        result = _bundle_url_output(spec)
        assert result is not None
        text = result.plain
        assert "Bundle URL" in text
        assert "https://example.com/bundles" in text

    def test_bundle_dir_no_matching_mapping(self) -> None:
        spec = FlowSpec(
            tasks=["t"],
            log_dir="./logs",
            options=FlowOptions(
                bundle_dir="/local/bundles",
                bundle_url_mappings={"/other": "https://example.com"},
            ),
        )
        result = _bundle_url_output(spec)
        assert result is not None
        assert "Bundle dir" in result.plain

    def test_bundle_dir_no_mappings(self) -> None:
        spec = FlowSpec(
            tasks=["t"],
            log_dir="./logs",
            options=FlowOptions(bundle_dir="/local/bundles"),
        )
        result = _bundle_url_output(spec)
        assert result is not None
        assert "Bundle dir" in result.plain
        assert result.plain.endswith("/local/bundles/")

    def test_bundle_dir_with_slash_no_mappings(self) -> None:
        spec = FlowSpec(
            tasks=["t"],
            log_dir="./logs",
            options=FlowOptions(bundle_dir="/local/bundles/"),
        )
        result = _bundle_url_output(spec)
        assert result is not None
        assert "Bundle dir" in result.plain
        assert result.plain.endswith("/local/bundles/")


# ── cli.py ──────────────────────────────────────────────────


class TestReadConfig:
    def test_reads_yaml_config(self, tmp_path: pytest.TempPathFactory) -> None:
        config_data = {"tasks": ["my_task"], "log_dir": "./logs"}
        config_file = tmp_path / "flow.yaml"  # type: ignore[operator]
        config_file.write_text(yaml.dump(config_data))
        spec = _read_config(str(config_file))
        assert isinstance(spec, FlowSpec)
        assert spec.tasks == ["my_task"]
        assert spec.log_dir == "./logs"


class TestFlowRunCli:
    def teardown_method(self) -> None:
        set_display(None)
        set_display_type("full")

    @patch("inspect_flow._runner.cli.signal_ready_and_wait")
    @patch("inspect_flow._runner.cli.run_eval_set")
    def test_invokes_run_eval_set(
        self,
        mock_run: MagicMock,
        mock_signal: MagicMock,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        mock_run.return_value = (True, [])
        config_data = {"tasks": ["my_task"], "log_dir": "./logs"}
        config_file = tmp_path / "flow.yaml"  # type: ignore[operator]
        config_file.write_text(yaml.dump(config_data))

        runner = CliRunner()
        result = runner.invoke(flow_run, ["--file", str(config_file)])
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        mock_signal.assert_called_once()
