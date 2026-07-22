import pickle
from collections.abc import Callable
from functools import partial
from typing import Any

import pytest
from inspect_ai import ScannerConfig, Task
from inspect_ai._util.registry import is_registry_object, registry_value
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog, EvalSpec
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
    FlowStoreConfig,
    FlowTask,
    log_filter,
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
    # either (or a string registry name) all serialize to a resolvable
    # reference.
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=a_task)]))
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=_top_level_task_factory)]))
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=FlowFactory(a_task))]))
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=FlowFactory("a_task"))]))


def test_flow_factory_wrapping_bad_callable_rejected() -> None:
    # The FlowFactory is unwrapped and its inner callable checked.
    spec = FlowSpec(tasks=[FlowTask(factory=FlowFactory(lambda: Task()))])
    violations = _violations(spec)
    assert [v.path for v in violations] == ["tasks[0].factory"]
    assert "cannot be recreated" in violations[0].message


def test_defaults_wrapper_factories_rejected() -> None:
    # Non-reconstructable factories in defaults.model/solver/agent and their
    # prefix mappings also make a spec non-portable, even though the venv path
    # would only surface them after defaults are merged into tasks.
    cases = [
        (
            FlowDefaults(model=FlowModel(factory=lambda: get_model("mockllm/model"))),
            "defaults.model.factory",
        ),
        (
            FlowDefaults(solver=FlowSolver(factory=lambda: a_solver())),
            "defaults.solver.factory",
        ),
        (
            FlowDefaults(agent=FlowAgent(factory=lambda: a_agent())),
            "defaults.agent.factory",
        ),
        (
            FlowDefaults(
                model_prefix={
                    "openai/": FlowModel(factory=lambda: get_model("mockllm/model"))
                }
            ),
            "defaults.model_prefix['openai/'].factory",
        ),
        (
            FlowDefaults(
                solver_prefix={"inspect/": FlowSolver(factory=lambda: a_solver())}
            ),
            "defaults.solver_prefix['inspect/'].factory",
        ),
        (
            FlowDefaults(
                agent_prefix={"inspect/": FlowAgent(factory=lambda: a_agent())}
            ),
            "defaults.agent_prefix['inspect/'].factory",
        ),
    ]
    for defaults, path in cases:
        violations = _violations(FlowSpec(defaults=defaults))
        assert [v.path for v in violations] == [path]
        assert "cannot be recreated" in violations[0].message


def test_defaults_wrappers_reconstructable_pass() -> None:
    validate_portable_spec(
        FlowSpec(
            defaults=FlowDefaults(
                model=FlowModel(name="mockllm/model"),
                solver=FlowSolver(name="a_solver"),
                agent=FlowAgent(name="a_agent"),
                model_prefix={"openai/": FlowModel(name="openai/gpt-4o")},
            )
        )
    )


@log_filter
def _keep_all(log: EvalLog) -> bool:
    return True


def test_store_filter_non_reconstructable_rejected() -> None:
    spec = FlowSpec(store=FlowStoreConfig(filter=lambda log: True))
    violations = _violations(spec)
    assert [v.path for v in violations] == ["store.filter"]
    assert "cannot be recreated" in violations[0].message

    spec = FlowSpec(store=FlowStoreConfig(filter=["keep_all", lambda log: True]))
    violations = _violations(spec)
    assert [v.path for v in violations] == ["store.filter[1]"]


def test_store_filter_reconstructable_passes() -> None:
    # A registered filter callable, a registry-name string, and a sequence of
    # them all serialize to a resolvable reference.
    validate_portable_spec(FlowSpec(store=FlowStoreConfig(filter=_keep_all)))
    validate_portable_spec(FlowSpec(store=FlowStoreConfig(filter="keep_all")))
    validate_portable_spec(
        FlowSpec(store=FlowStoreConfig(filter=[_keep_all, "keep_all"]))
    )


def test_lossy_values_in_containers_rejected() -> None:
    # Free-form value containers (metadata, args, scanner params, factory args)
    # must not smuggle a live object past the check, since it serializes to a
    # repr string and reloads as that string in the child.
    cases = [
        (FlowSpec(flow_metadata={"x": Task()}), "flow_metadata"),
        (FlowSpec(options=FlowOptions(metadata={"x": Task()})), "options.metadata"),
        (FlowSpec(tasks=[FlowTask(name="t", args={"x": Task()})]), "tasks[0].args"),
        (
            FlowSpec(tasks=[FlowTask(name="t", metadata={"x": Task()})]),
            "tasks[0].metadata",
        ),
        (
            FlowSpec(tasks=[FlowTask(name="t", flow_metadata={"x": Task()})]),
            "tasks[0].flow_metadata",
        ),
        (
            FlowSpec(
                tasks=[FlowTask(model=FlowModel(name="m", flow_metadata={"x": Task()}))]
            ),
            "tasks[0].model.flow_metadata",
        ),
        (
            FlowSpec(tasks=[FlowTask(factory=FlowFactory("reg", args={"x": Task()}))]),
            "tasks[0].factory.args",
        ),
        (
            FlowSpec(
                options=FlowOptions(
                    scanner=ScannerConfig(
                        scanners=[ScannerSpec(name="kw", params={"x": Task()})]
                    )
                )
            ),
            "options.scanner.scanners[0].params",
        ),
    ]
    for spec, path in cases:
        violations = _violations(spec)
        assert [v.path for v in violations] == [path]
        assert "cannot be serialized" in violations[0].message


def test_portable_values_in_containers_pass() -> None:
    from datetime import datetime

    # JSON data, natively-serialized types (datetime), and a nested structure
    # all round-trip; only genuinely lossy leaves are rejected.
    validate_portable_spec(
        FlowSpec(
            flow_metadata={
                "n": 1,
                "items": [1, 2, {"k": "v"}],
                "when": datetime(2020, 1, 1),
            },
            tasks=[FlowTask(name="t", args={"threshold": 0.5, "labels": ["a", "b"]})],
        )
    )


def _serializes_lossily(obj: Any) -> bool:
    # Independent mirror of _serialize_fallback's branches: a value that reaches
    # pydantic's dump fallback is lossy unless it becomes a registry dict (which
    # round-trips) or a resolvable callable name (registry object or a
    # module-level function).
    value = registry_value(obj)
    if isinstance(value, dict):
        return False
    if callable(value):
        code = getattr(value, "__code__", None)
        return not (
            is_registry_object(value)
            or (
                code is not None
                and value.__name__ != "<lambda>"
                and getattr(value, "__qualname__", value.__name__) == value.__name__
            )
        )
    return True


def _lossy_leaf_count(spec: FlowSpec) -> int:
    coerced: list[Any] = []
    spec.model_dump(mode="json", exclude_unset=True, fallback=coerced.append)
    return sum(1 for obj in coerced if _serializes_lossily(obj))


def test_validator_flags_every_lossy_leaf() -> None:
    # Completeness oracle. Pydantic's own dump traverses every field; any value
    # that serializes lossily (a repr, or an unresolvable callable name) must be
    # reported by the validator, or the child process gets a corrupt spec. This
    # catches a lossy value in any field populated below that the validator
    # misses; the field-name snapshot test surfaces new fields to populate. This
    # does not cover live objects that serialize to a round-trippable registry
    # dict (Model/Scorer/Solver/Agent) — the validator rejects those as a
    # stance, tested separately.
    bad_task = FlowTask(
        factory=lambda: Task(),
        args={"x": Task()},
        metadata={"x": Task()},
        flow_metadata={"x": Task()},
        model=FlowModel(factory=lambda: get_model("mockllm/model")),
        model_roles={"grader": FlowModel(factory=lambda: get_model("mockllm/model"))},
        scorer=[FlowScorer(factory=lambda: a_scorer())],
        solver=[FlowSolver(factory=lambda: a_solver())],
        early_stopping=_LiveEarlyStopping(),
    )
    spec = FlowSpec(
        tasks=[Task(), bad_task],
        flow_metadata={"x": Task()},
        options=FlowOptions(
            metadata={"x": Task()},
            scanner=ScannerConfig(
                scanners=[ScannerSpec(name="kw", params={"x": Task()})]
            ),
        ),
        defaults=FlowDefaults(
            task=FlowTask(factory=lambda: Task()),
            task_prefix={"p/": FlowTask(factory=lambda: Task())},
            model=FlowModel(factory=lambda: get_model("mockllm/model")),
            solver=FlowSolver(factory=lambda: a_solver()),
            agent=FlowAgent(factory=lambda: a_agent()),
            model_prefix={"m/": FlowModel(factory=lambda: get_model("mockllm/model"))},
            solver_prefix={"s/": FlowSolver(factory=lambda: a_solver())},
            agent_prefix={"a/": FlowAgent(factory=lambda: a_agent())},
        ),
        store=FlowStoreConfig(filter=lambda log: True),
    )
    with pytest.raises(SpecNotPortableError) as excinfo:
        validate_portable_spec(spec)
    assert sorted(v.path for v in excinfo.value.violations) == sorted(
        [
            "tasks[0]",
            "tasks[1].factory",
            "tasks[1].args",
            "tasks[1].metadata",
            "tasks[1].flow_metadata",
            "tasks[1].model.factory",
            "tasks[1].model_roles['grader'].factory",
            "tasks[1].scorer[0].factory",
            "tasks[1].solver[0].factory",
            "tasks[1].early_stopping",
            "flow_metadata",
            "options.metadata",
            "options.scanner.scanners[0].params",
            "defaults.task.factory",
            "defaults.task_prefix['p/'].factory",
            "defaults.model.factory",
            "defaults.solver.factory",
            "defaults.agent.factory",
            "defaults.model_prefix['m/'].factory",
            "defaults.solver_prefix['s/'].factory",
            "defaults.agent_prefix['a/'].factory",
            "store.filter",
        ]
    )
    # Independent cross-check: pydantic coerced exactly as many lossy leaves as
    # the validator reported violations. If a populated field serialized lossily
    # but the validator missed it, these diverge and the test fails.
    assert _lossy_leaf_count(spec) == len(excinfo.value.violations)


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
    assert sorted(FlowStoreConfig.model_fields) == [
        "filter",
        "path",
        "read",
        "write",
    ]
    assert sorted(FlowFactory.model_fields) == [
        "args",
        "factory",
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
