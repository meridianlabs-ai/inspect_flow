import pickle
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from functools import partial

import pytest
import yaml
from inspect_ai import ScannerConfig, Task
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog, EvalSpec
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.scorer import SampleScore
from inspect_ai.util import EarlyStop
from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowEpochs,
    FlowExtraArgs,
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
from inspect_flow._config.write import config_to_yaml
from inspect_flow.api import (
    SpecNotPortableError,
    SpecViolation,
    validate_portable_spec,
)
from inspect_scout import ScannerSpec
from local_eval.my_scanners import keyword_scanner
from pydantic import JsonValue

from tests.config.inspect_objects_flow import a_agent, a_scorer, a_solver, a_task


def _paths(spec: FlowSpec) -> list[str]:
    with pytest.raises(SpecNotPortableError) as excinfo:
        validate_portable_spec(spec)
    return [v.path for v in excinfo.value.violations]


def _message(spec: FlowSpec) -> str:
    with pytest.raises(SpecNotPortableError) as excinfo:
        validate_portable_spec(spec)
    return excinfo.value.violations[0].message


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


# -- Live Inspect objects --


def test_live_inspect_objects_rejected() -> None:
    cases = [
        (FlowSpec(tasks=[Task()]), "tasks[0]", "Task"),
        (
            FlowSpec(tasks=[FlowTask(model=get_model("mockllm/model"))]),
            "tasks[0].model",
            "Model",
        ),
        (
            FlowSpec(tasks=[FlowTask(model_roles={"grader": get_model("mockllm/m")})]),
            "tasks[0].model_roles['grader']",
            "Model",
        ),
        (FlowSpec(tasks=[FlowTask(scorer=a_scorer())]), "tasks[0].scorer", "Scorer"),
        (
            FlowSpec(tasks=[FlowTask(scorer=[a_scorer()])]),
            "tasks[0].scorer[0]",
            "Scorer",
        ),
        (FlowSpec(tasks=[FlowTask(solver=a_solver())]), "tasks[0].solver", "Solver"),
        (
            FlowSpec(tasks=[FlowTask(solver=["plan", a_solver()])]),
            "tasks[0].solver[1]",
            "Solver",
        ),
        (FlowSpec(tasks=[FlowTask(solver=a_agent())]), "tasks[0].solver", "Agent"),
        (
            FlowSpec(tasks=[FlowTask(early_stopping=_LiveEarlyStopping())]),
            "tasks[0].early_stopping",
            "",
        ),
    ]
    for spec, path, kind in cases:
        assert _paths(spec) == [path]
        if kind:
            # The registry type, not isinstance, picks the label: Scorer/Solver/
            # Agent are Protocols that any callable satisfies structurally.
            assert f"already-instantiated {kind} object" in _message(spec)


def test_live_objects_in_defaults_templates_rejected() -> None:
    spec = FlowSpec(
        defaults=FlowDefaults(
            task=FlowTask(model=get_model("mockllm/model")),
            task_prefix={"swe/": FlowTask(scorer=[a_scorer()])},
        )
    )
    assert sorted(_paths(spec)) == [
        "defaults.task.model",
        "defaults.task_prefix['swe/'].scorer[0]",
    ]


# -- Callables --


def _top_level_task_factory() -> Task:
    return Task()


def _returns_nested_factory() -> Callable[[], Task]:
    def nested() -> Task:
        return Task()

    return nested


class _CallableFactory:
    def __call__(self) -> Task:
        return Task()


def test_non_nameable_callables_rejected() -> None:
    factories: list[Callable[..., Task]] = [
        lambda: Task(),
        partial(Task),
        _returns_nested_factory(),
        _CallableFactory(),
    ]
    for factory in factories:
        spec = FlowSpec(tasks=[FlowTask(factory=factory)])
        assert _paths(spec) == ["tasks[0].factory"]
        assert "cannot be named again" in _message(spec)


def test_non_nameable_callables_in_wrappers_rejected() -> None:
    cases = [
        (
            FlowTask(model=FlowModel(factory=lambda: get_model("mockllm/model"))),
            "tasks[0].model.factory",
        ),
        (
            FlowTask(model_roles={"grader": FlowModel(factory=lambda: get_model("m"))}),
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
        (
            FlowTask(factory=FlowFactory(lambda: Task())),
            "tasks[0].factory.factory",
        ),
    ]
    for task, path in cases:
        assert _paths(FlowSpec(tasks=[task])) == [path]


def test_non_nameable_callables_in_defaults_rejected() -> None:
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
                model_prefix={"m/": FlowModel(factory=lambda: get_model("m"))}
            ),
            "defaults.model_prefix['m/'].factory",
        ),
        (
            FlowDefaults(solver_prefix={"s/": FlowSolver(factory=lambda: a_solver())}),
            "defaults.solver_prefix['s/'].factory",
        ),
        (
            FlowDefaults(agent_prefix={"a/": FlowAgent(factory=lambda: a_agent())}),
            "defaults.agent_prefix['a/'].factory",
        ),
    ]
    for defaults, path in cases:
        assert _paths(FlowSpec(defaults=defaults)) == [path]


def test_nameable_callables_pass() -> None:
    # A registry object, a module-level function, and FlowFactory wrapping
    # either (or a registry-name string) all serialize to a resolvable name.
    for factory in (a_task, _top_level_task_factory, FlowFactory(a_task)):
        validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=factory)]))
    validate_portable_spec(FlowSpec(tasks=[FlowTask(factory=FlowFactory("a_task"))]))


# -- Free-form value containers --


def test_lossy_values_in_containers_rejected() -> None:
    cases = [
        (FlowSpec(flow_metadata={"x": Task()}), "flow_metadata['x']"),
        (
            FlowSpec(options=FlowOptions(metadata={"x": Task()})),
            "options.metadata['x']",
        ),
        (
            FlowSpec(tasks=[FlowTask(name="t", args={"x": Task()})]),
            "tasks[0].args['x']",
        ),
        (
            FlowSpec(tasks=[FlowTask(name="t", metadata={"x": Task()})]),
            "tasks[0].metadata['x']",
        ),
        (
            FlowSpec(tasks=[FlowTask(name="t", flow_metadata={"x": Task()})]),
            "tasks[0].flow_metadata['x']",
        ),
        (
            FlowSpec(
                tasks=[
                    FlowTask(name="t", extra_args=FlowExtraArgs(model={"x": Task()}))
                ]
            ),
            "tasks[0].extra_args.model['x']",
        ),
        (
            FlowSpec(
                tasks=[FlowTask(model=FlowModel(name="m", model_args={"x": Task()}))]
            ),
            "tasks[0].model.model_args['x']",
        ),
        (
            FlowSpec(
                tasks=[FlowTask(scorer=[FlowScorer(name="s", args={"x": Task()})])]
            ),
            "tasks[0].scorer[0].args['x']",
        ),
        (
            FlowSpec(
                tasks=[FlowTask(model=FlowModel(name="m", flow_metadata={"x": Task()}))]
            ),
            "tasks[0].model.flow_metadata['x']",
        ),
        (
            FlowSpec(tasks=[FlowTask(factory=FlowFactory("reg", args={"x": Task()}))]),
            "tasks[0].factory.args['x']",
        ),
        (
            FlowSpec(
                tasks=[FlowTask(name="t", metadata={"nested": [{"deep": Task()}]})]
            ),
            "tasks[0].metadata['nested'][0]['deep']",
        ),
    ]
    for spec, path in cases:
        assert _paths(spec) == [path]


def test_live_object_in_container_rejected_like_anywhere_else() -> None:
    # A registered object serializes to a registry dict, but the child reloads
    # that as a plain dict rather than the object, so it is not portable here
    # either -- the same rule as in a structural position.
    spec = FlowSpec(tasks=[FlowTask(name="t", metadata={"s": a_scorer()})])
    assert _paths(spec) == ["tasks[0].metadata['s']"]


def test_portable_values_in_containers_pass() -> None:
    validate_portable_spec(
        FlowSpec(
            flow_metadata={
                "n": 1,
                "items": [1, 2, {"k": "v"}],
                "when": datetime(2020, 1, 1),
                "flag": None,
            },
            tasks=[
                FlowTask(
                    name="t",
                    args={"threshold": 0.5, "labels": ["a", "b"]},
                    metadata={},
                )
            ],
        )
    )


# -- Store filter --


@log_filter
def _keep_all(log: EvalLog) -> bool:
    return True


def test_store_filter() -> None:
    assert _paths(FlowSpec(store=FlowStoreConfig(filter=lambda log: True))) == [
        "store.filter"
    ]
    assert _paths(
        FlowSpec(store=FlowStoreConfig(filter=["keep_all", lambda log: True]))
    ) == ["store.filter[1]"]
    # A registered filter, a registry-name string, and a sequence of them all
    # resolve again in the child.
    validate_portable_spec(FlowSpec(store=FlowStoreConfig(filter=_keep_all)))
    validate_portable_spec(FlowSpec(store=FlowStoreConfig(filter="keep_all")))
    validate_portable_spec(
        FlowSpec(store=FlowStoreConfig(filter=[_keep_all, "keep_all"]))
    )


# -- Scanners --


def test_live_scanners_rejected() -> None:
    cases = [
        ((keyword_scanner(),), "options.scanner.scanners[0]"),
        ([("kw", keyword_scanner())], "options.scanner.scanners[0][1]"),
        (keyword_scanner(), "options.scanner.scanners"),
        ({"kw": keyword_scanner()}, "options.scanner.scanners['kw']"),
    ]
    for scanners, path in cases:
        spec = FlowSpec(options=FlowOptions(scanner=ScannerConfig(scanners=scanners)))
        assert _paths(spec) == [path]

    specs = [{"name": "keyword_scanner"}]
    assert _paths(
        FlowSpec(
            options=FlowOptions(
                scanner=ScannerConfig(scanners=specs, model=get_model("mockllm/model"))
            )
        )
    ) == ["options.scanner.model"]
    assert _paths(
        FlowSpec(
            options=FlowOptions(
                scanner=ScannerConfig(
                    scanners=specs, model_roles={"grader": get_model("mockllm/model")}
                )
            )
        )
    ) == ["options.scanner.model_roles['grader']"]
    assert _paths(
        FlowSpec(
            options=FlowOptions(
                scanner=ScannerConfig(
                    scanners=[ScannerSpec(name="kw", params={"x": Task()})]
                )
            )
        )
    ) == ["options.scanner.scanners[0].params['x']"]


def test_serializable_scanners_pass() -> None:
    # A config file path, spec references in any shape, and a bare registry
    # name all survive the boundary unchanged.
    for scanner in (
        "tests/config/scanners.yaml",
        ScannerConfig(scanners=["keyword_scanner"]),
        ScannerConfig(scanners=[{"name": "keyword_scanner"}]),
        ScannerConfig(scanners=[ScannerSpec(name="keyword_scanner")]),
        ScannerConfig(scanners={"kw": {"name": "keyword_scanner"}}),
        ScannerConfig(scanners=ScannerSpec(name="keyword_scanner")),
    ):
        validate_portable_spec(FlowSpec(options=FlowOptions(scanner=scanner)))


# -- Error shape --


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
    assert sorted(v.path for v in error.violations) == [
        "defaults.task.scorer",
        "tasks[0].model",
        "tasks[0].solver",
        "tasks[2]",
    ]
    message = str(error)
    assert "not portable" in message
    for violation in error.violations:
        assert f"{violation.path}: {violation.message}" in message


def test_error_pickles() -> None:
    # Remote orchestrators may move the error across process boundaries.
    error = SpecNotPortableError([SpecViolation("tasks[0]", "message")], hint="a hint")
    restored = pickle.loads(pickle.dumps(error))
    assert restored.violations == error.violations
    assert restored.hint == error.hint
    assert str(restored) == str(error)


# -- Ground truth: agreement with the real boundary --


def _reload(spec: FlowSpec) -> FlowSpec:
    """Reproduce what the child process does with a serialized spec."""
    return FlowSpec.model_validate(yaml.safe_load(config_to_yaml(spec)))


def _first_task(spec: FlowSpec) -> object:
    tasks = spec.tasks
    assert isinstance(tasks, Sequence) and not isinstance(tasks, str)
    return tasks[0]


def _task_attr(name: str) -> Callable[[FlowSpec], object]:
    # getattr rather than attribute access: the reloaded value has a different
    # type than the original, which is exactly what these cases assert.
    return lambda spec: getattr(_first_task(spec), name)


def _task_metadata(key: str) -> Callable[[FlowSpec], object]:
    def get(spec: FlowSpec) -> object:
        metadata = _task_attr("metadata")(spec)
        assert isinstance(metadata, Mapping)
        return metadata[key]

    return get


def _store_filter(spec: FlowSpec) -> object:
    store = spec.store
    assert isinstance(store, FlowStoreConfig)
    return store.filter


def _fully_populated_portable_spec() -> FlowSpec:
    return FlowSpec(
        log_dir="logs",
        execution_type="venv",
        flow_metadata={"owner": "team", "when": datetime(2020, 1, 1)},
        store=FlowStoreConfig(filter=[_keep_all, "keep_all"], read=True),
        options=FlowOptions(
            metadata={"run": 1},
            limit=(9, 20),
            scanner=ScannerConfig(scanners=[ScannerSpec(name="keyword_scanner")]),
        ),
        defaults=FlowDefaults(
            config=GenerateConfig(temperature=0.5),
            model=FlowModel(name="mockllm/model"),
            task=FlowTask(epochs=FlowEpochs(epochs=2, reducer="mean")),
            model_prefix={"openai/": FlowModel(name="openai/gpt-4o")},
        ),
        tasks=[
            "local_eval/noop",
            FlowTask(
                name="local_eval/noop",
                factory=a_task,
                args={"threshold": 0.5},
                model="mockllm/model",
                model_roles={"grader": FlowModel(name="mockllm/model")},
                solver=[FlowSolver(name="a_solver")],
                scorer=["a_scorer"],
                extra_args=FlowExtraArgs(model={"timeout": 30}),
                metadata={"tag": "x"},
                token_limit="1M",
                epochs=3,
            ),
        ],
    )


def test_validated_spec_survives_the_real_boundary() -> None:
    # The contract, asserted against the code path the child actually runs:
    # if validate_portable_spec passes, dumping and reloading reproduces the
    # spec. This is the ground truth the validator is an approximation of.
    spec = _fully_populated_portable_spec()
    validate_portable_spec(spec)
    reloaded = _reload(spec)
    assert config_to_yaml(reloaded) == config_to_yaml(spec)


def test_rejected_specs_do_not_survive_the_real_boundary() -> None:
    # The other direction: each rejected spec genuinely fails to come back --
    # either the child cannot validate it at all, or the value it reloads is a
    # different thing (a repr string, an unresolvable name, a plain dict) than
    # the parent had. A validator that flagged a portable value would fail here.
    cases: list[tuple[FlowSpec, Callable[[FlowSpec], object]]] = [
        (FlowSpec(tasks=[Task()]), _first_task),
        (FlowSpec(tasks=[FlowTask(scorer=a_scorer())]), _task_attr("scorer")),
        (FlowSpec(tasks=[FlowTask(solver=a_solver())]), _task_attr("solver")),
        (
            FlowSpec(tasks=[FlowTask(model=get_model("mockllm/model"))]),
            _task_attr("model"),
        ),
        (FlowSpec(tasks=[FlowTask(factory=lambda: Task())]), _task_attr("factory")),
        (
            FlowSpec(tasks=[FlowTask(name="t", metadata={"x": Task()})]),
            _task_metadata("x"),
        ),
        (
            FlowSpec(tasks=[FlowTask(name="t", metadata={"s": a_scorer()})]),
            _task_metadata("s"),
        ),
        (FlowSpec(store=FlowStoreConfig(filter=lambda log: True)), _store_filter),
    ]
    for spec, offending in cases:
        with pytest.raises(SpecNotPortableError):
            validate_portable_spec(spec)
        try:
            reloaded = _reload(spec)
        except Exception:
            continue  # the child rejects it outright
        assert type(offending(spec)) is not type(offending(reloaded))


def test_completeness_against_the_dump() -> None:
    # Completeness oracle: pydantic's own traversal decides which leaves are
    # coerced; every one that cannot be reloaded must be reported. A new field
    # carrying such a value fails here rather than reaching a runner.
    spec = FlowSpec(
        tasks=[
            Task(),
            FlowTask(
                factory=lambda: Task(),
                args={"x": Task()},
                metadata={"x": Task()},
                model=FlowModel(factory=lambda: get_model("mockllm/model")),
                model_roles={"grader": FlowModel(factory=lambda: get_model("m"))},
                scorer=[FlowScorer(factory=lambda: a_scorer())],
                solver=[FlowSolver(factory=lambda: a_solver())],
                early_stopping=_LiveEarlyStopping(),
            ),
        ],
        flow_metadata={"x": Task()},
        options=FlowOptions(
            metadata={"x": Task()},
            scanner=ScannerConfig(
                scanners=[ScannerSpec(name="kw", params={"x": Task()})]
            ),
        ),
        defaults=FlowDefaults(
            task=FlowTask(factory=lambda: Task()),
            model=FlowModel(factory=lambda: get_model("mockllm/model")),
            solver=FlowSolver(factory=lambda: a_solver()),
            agent=FlowAgent(factory=lambda: a_agent()),
        ),
        store=FlowStoreConfig(filter=lambda log: True),
    )
    assert sorted(_paths(spec)) == sorted(
        [
            "tasks[0]",
            "tasks[1].factory",
            "tasks[1].args['x']",
            "tasks[1].metadata['x']",
            "tasks[1].model.factory",
            "tasks[1].model_roles['grader'].factory",
            "tasks[1].scorer[0].factory",
            "tasks[1].solver[0].factory",
            "tasks[1].early_stopping",
            "flow_metadata['x']",
            "options.metadata['x']",
            "options.scanner.scanners[0].params['x']",
            "defaults.task.factory",
            "defaults.model.factory",
            "defaults.solver.factory",
            "defaults.agent.factory",
            "store.filter",
        ]
    )
