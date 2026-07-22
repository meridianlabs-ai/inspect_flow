import pickle
from collections.abc import Callable
from functools import partial

import pytest
from inspect_ai import ScannerConfig, Task
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalSpec
from inspect_ai.model import get_model
from inspect_ai.scorer import SampleScore
from inspect_ai.util import EarlyStop
from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowFactory,
    FlowModel,
    FlowOptions,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowTask,
)
from inspect_flow.api import (
    SpecNotPortableError,
    SpecViolation,
    validate_portable_spec,
)
from inspect_scout import ScannerSpec
from local_eval.my_scanners import keyword_scanner
from pydantic import JsonValue

from tests.config.inspect_objects_flow import a_agent, a_scorer, a_solver, a_task


def _violations(spec: FlowSpec) -> list[SpecViolation]:
    with pytest.raises(SpecNotPortableError) as excinfo:
        validate_portable_spec(spec)
    return excinfo.value.violations


class _LiveEarlyStopping:
    async def start_task(
        self, task: EvalSpec, samples: list[Sample], epochs: int
    ) -> str:
        return "live"

    async def schedule_sample(self, id: str | int, epoch: int) -> EarlyStop | None:
        return None

    async def complete_sample(
        self, id: str | int, epoch: int, scores: dict[str, SampleScore]
    ) -> None:
        return None

    async def complete_task(self) -> dict[str, JsonValue]:
        return {}


def test_live_task_rejected() -> None:
    violations = _violations(FlowSpec(tasks=[Task()]))
    assert [v.path for v in violations] == ["tasks[0]"]
    assert "already-instantiated Task object" in violations[0].message


def test_live_model_rejected() -> None:
    spec = FlowSpec(tasks=[FlowTask(model=get_model("mockllm/model"))])
    violations = _violations(spec)
    assert [v.path for v in violations] == ["tasks[0].model"]
    assert "already-instantiated Model object" in violations[0].message


def test_live_model_in_model_roles_rejected() -> None:
    spec = FlowSpec(
        tasks=[FlowTask(model_roles={"grader": get_model("mockllm/model")})]
    )
    violations = _violations(spec)
    assert [v.path for v in violations] == ["tasks[0].model_roles['grader']"]
    assert "already-instantiated Model object" in violations[0].message


def test_live_scorer_rejected() -> None:
    violations = _violations(FlowSpec(tasks=[FlowTask(scorer=a_scorer())]))
    assert [v.path for v in violations] == ["tasks[0].scorer"]
    assert "already-instantiated Scorer object" in violations[0].message

    # sequence form was a gap in the private check
    violations = _violations(FlowSpec(tasks=[FlowTask(scorer=[a_scorer()])]))
    assert [v.path for v in violations] == ["tasks[0].scorer[0]"]


def test_live_solver_rejected() -> None:
    violations = _violations(FlowSpec(tasks=[FlowTask(solver=a_solver())]))
    assert [v.path for v in violations] == ["tasks[0].solver"]
    assert "already-instantiated Solver or Agent" in violations[0].message

    violations = _violations(FlowSpec(tasks=[FlowTask(solver=a_agent())]))
    assert [v.path for v in violations] == ["tasks[0].solver"]

    violations = _violations(FlowSpec(tasks=[FlowTask(solver=["plan", a_solver()])]))
    assert [v.path for v in violations] == ["tasks[0].solver[1]"]


def test_live_early_stopping_rejected() -> None:
    spec = FlowSpec(tasks=[FlowTask(early_stopping=_LiveEarlyStopping())])
    violations = _violations(spec)
    assert [v.path for v in violations] == ["tasks[0].early_stopping"]
    assert "early_stopping" in violations[0].message


def _top_level_task_factory() -> Task:
    return Task()


def _returns_nested_factory() -> Callable[[], Task]:
    def nested() -> Task:
        return Task()

    return nested


class _CallableFactory:
    def __call__(self) -> Task:
        return Task()


def test_non_reconstructable_factory_rejected() -> None:
    # A lambda, partial, nested function, or callable object serializes to an
    # unresolvable reference (or crashes serialization), so a spec carrying one
    # is not portable even though it is a callable.
    factories: list[Callable[..., Task]] = [
        lambda: Task(),
        partial(Task),
        _returns_nested_factory(),
        _CallableFactory(),
    ]
    for factory in factories:
        violations = _violations(FlowSpec(tasks=[FlowTask(factory=factory)]))
        assert [v.path for v in violations] == ["tasks[0].factory"]
        assert "cannot be recreated" in violations[0].message


def test_non_reconstructable_factory_in_wrappers_rejected() -> None:
    cases = [
        (
            FlowTask(model=FlowModel(factory=lambda: get_model("mockllm/model"))),
            "tasks[0].model.factory",
        ),
        (
            FlowTask(
                model_roles={"grader": FlowModel(factory=lambda: get_model("m/m"))}
            ),
            "tasks[0].model_roles['grader'].factory",
        ),
        (
            FlowTask(scorer=[FlowScorer(factory=lambda: a_scorer())]),
            "tasks[0].scorer[0].factory",
        ),
        (
            FlowTask(solver=[FlowSolver(factory=lambda: a_solver())]),
            "tasks[0].solver[0].factory",
        ),
        (
            FlowTask(solver=FlowAgent(factory=lambda: a_agent())),
            "tasks[0].solver.factory",
        ),
    ]
    for task, path in cases:
        violations = _violations(FlowSpec(tasks=[task]))
        assert [v.path for v in violations] == [path]
        assert "cannot be recreated" in violations[0].message


def test_reconstructable_factories_pass() -> None:
    # A registry object, a module-level function, and FlowFactory wrapping
    # either all serialize to a resolvable reference.
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=a_task)]))
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=_top_level_task_factory)]))
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=FlowFactory(a_task))]))


def test_defaults_task_templates_rejected() -> None:
    # defaults.task and defaults.task_prefix were gaps in the private check
    spec = FlowSpec(
        defaults=FlowDefaults(
            task=FlowTask(model=get_model("mockllm/model")),
            task_prefix={"swe/": FlowTask(scorer=[a_scorer()])},
        )
    )
    violations = _violations(spec)
    assert [v.path for v in violations] == [
        "defaults.task.model",
        "defaults.task_prefix['swe/'].scorer[0]",
    ]


def test_live_scanner_rejected() -> None:
    # Every shape that carries a live Scanner (any sequence, scout's
    # (name, Scanner) tuples, a bare scanner, bare strings, dicts) is
    # rejected, with a path matching the shape.
    for scanners, path in (
        ((keyword_scanner(),), "options.scanner.scanners[0]"),
        ([("kw", keyword_scanner())], "options.scanner.scanners[0]"),
        (keyword_scanner(), "options.scanner.scanners"),
        (["keyword_scanner"], "options.scanner.scanners[0]"),
        ({"kw": keyword_scanner()}, "options.scanner.scanners['kw']"),
    ):
        spec = FlowSpec(options=FlowOptions(scanner=ScannerConfig(scanners=scanners)))
        violations = _violations(spec)
        assert [v.path for v in violations] == [path]
        assert "not serializable spec references" in violations[0].message


def test_error_pickles() -> None:
    # Remote orchestrators may move the error across process boundaries.
    error = SpecNotPortableError([SpecViolation("tasks[0]", "message")], hint="a hint")
    restored = pickle.loads(pickle.dumps(error))
    assert restored.violations == error.violations
    assert restored.hint == error.hint
    assert str(restored) == str(error)


def test_live_scanner_model_rejected() -> None:
    specs = [{"name": "keyword_scanner"}]
    scanner = ScannerConfig(scanners=specs, model=get_model("mockllm/model"))
    spec = FlowSpec(options=FlowOptions(scanner=scanner))
    violations = _violations(spec)
    assert [v.path for v in violations] == ["options.scanner.model"]
    assert "Model object as the ScannerConfig model" in violations[0].message

    scanner = ScannerConfig(
        scanners=specs, model_roles={"grader": get_model("mockllm/model")}
    )
    spec = FlowSpec(options=FlowOptions(scanner=scanner))
    violations = _violations(spec)
    assert [v.path for v in violations] == ["options.scanner.model_roles['grader']"]


def test_collects_all_violations() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(model=get_model("mockllm/model"), solver=a_solver()),
            "local_eval/noop",
            Task(),
        ],
        defaults=FlowDefaults(task=FlowTask(scorer=a_scorer())),
    )
    with pytest.raises(SpecNotPortableError) as excinfo:
        validate_portable_spec(spec)
    error = excinfo.value
    assert [v.path for v in error.violations] == [
        "tasks[0].model",
        "tasks[0].solver",
        "tasks[2]",
        "defaults.task.scorer",
    ]
    # str() renders a header plus one line per violation
    message = str(error)
    assert "not portable" in message
    for violation in error.violations:
        assert f"{violation.path}: {violation.message}" in message


def test_portable_spec_passes() -> None:
    validate_portable_spec(FlowSpec())
    spec = FlowSpec(
        tasks=[
            "local_eval/noop",
            FlowTask(
                name="local_eval/noop",
                model="mockllm/model",
                model_roles={"grader": FlowModel(name="mockllm/model")},
                solver=[FlowSolver(name="a_solver")],
                scorer=["a_scorer"],
            ),
            # factory callables serialize via registry/file reference: allowed
            FlowTask(factory=a_task),
        ],
        defaults=FlowDefaults(
            task=FlowTask(model=FlowModel(name="mockllm/model")),
            task_prefix={"swe/": FlowTask(scorer="a_scorer")},
        ),
        options=FlowOptions(
            scanner=ScannerConfig(scanners=[ScannerSpec(name="keyword_scanner")])
        ),
    )
    validate_portable_spec(spec)


def test_scanner_config_shapes_pass() -> None:
    # A config file path, or a config whose scanners are all spec references
    # (list or dict of dicts / ScannerSpec instances, or a bare ScannerSpec).
    for scanner in (
        "tests/config/scanners.yaml",
        ScannerConfig(scanners=[{"name": "keyword_scanner"}]),
        ScannerConfig(scanners=[ScannerSpec(name="keyword_scanner")]),
        ScannerConfig(scanners={"kw": {"name": "keyword_scanner"}}),
        ScannerConfig(scanners=ScannerSpec(name="keyword_scanner")),
    ):
        validate_portable_spec(FlowSpec(options=FlowOptions(scanner=scanner)))


def test_spec_fields_are_classified_for_portability() -> None:
    # If this test fails, you added or renamed a field on a spec type. Decide
    # whether the field can hold live (non-serializable) Inspect objects:
    #   - if it can, extend validate_portable_spec in
    #     src/inspect_flow/_config/portable.py (and the coverage list in
    #     design/portable_spec_validation.md), then update the snapshot;
    #   - if it cannot, just update the snapshot.
    assert sorted(FlowSpec.model_fields) == [
        "defaults",
        "dependencies",
        "env",
        "execution_type",
        "flow_metadata",
        "includes",
        "instantiate",
        "internal",
        "log_dir",
        "log_dir_create_unique",
        "options",
        "python_version",
        "store",
        "tasks",
    ]
    assert sorted(FlowTask.model_fields) == [
        "approval",
        "args",
        "checkpoint",
        "config",
        "continue_on_fail",
        "cost_limit",
        "early_stopping",
        "epochs",
        "extra_args",
        "factory",
        "fail_on_error",
        "flow_metadata",
        "message_limit",
        "metadata",
        "model",
        "model_roles",
        "name",
        "sample_id",
        "sandbox",
        "score_on_error",
        "scorer",
        "solver",
        "tags",
        "time_limit",
        "token_limit",
        "turn_limit",
        "version",
        "working_limit",
    ]
    assert sorted(FlowDefaults.model_fields) == [
        "agent",
        "agent_prefix",
        "config",
        "model",
        "model_prefix",
        "solver",
        "solver_prefix",
        "task",
        "task_prefix",
    ]
    assert sorted(FlowModel.model_fields) == [
        "api_key",
        "base_url",
        "config",
        "default",
        "factory",
        "flow_metadata",
        "memoize",
        "model_args",
        "name",
        "role",
    ]
    assert sorted(FlowScorer.model_fields) == [
        "args",
        "factory",
        "flow_metadata",
        "name",
    ]
    assert sorted(FlowSolver.model_fields) == [
        "args",
        "factory",
        "flow_metadata",
        "name",
    ]
    assert sorted(FlowAgent.model_fields) == [
        "args",
        "factory",
        "flow_metadata",
        "name",
        "type",
    ]
    assert sorted(FlowOptions.model_fields) == [
        "acp_server",
        "approval",
        "bundle_dir",
        "bundle_overwrite",
        "bundle_url_mappings",
        "checkpoint",
        "continue_on_fail",
        "ctl_server",
        "debug_errors",
        "display",
        "embed_viewer",
        "eval_set_id",
        "fail_on_error",
        "limit",
        "log_buffer",
        "log_dir_allow_dirty",
        "log_format",
        "log_images",
        "log_level",
        "log_level_transcript",
        "log_model_api",
        "log_realtime",
        "log_refusals",
        "log_samples",
        "log_shared",
        "max_dataset_memory",
        "max_samples",
        "max_sandboxes",
        "max_subprocesses",
        "max_tasks",
        "metadata",
        "model_cost_config",
        "notification",
        "retry_attempts",
        "retry_cleanup",
        "retry_connections",
        "retry_on_error",
        "retry_wait",
        "sample_shuffle",
        "sandbox",
        "sandbox_cleanup",
        "scanner",
        "score",
        "score_display",
        "score_on_error",
        "tags",
        "trace",
    ]
