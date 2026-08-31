from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from inspect_ai import ScannerConfig, Task
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowExtraArgs,
    FlowFactory,
    FlowModel,
    FlowOptions,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowTask,
)
from inspect_flow._config.defaults import apply_defaults
from inspect_flow._util.pydantic_util import model_dump
from inspect_flow.api import SpecModelRef, iter_model_refs, load_spec
from pydantic import BaseModel


def _refs(spec: FlowSpec) -> list[tuple[str, str | None, str | None]]:
    return [(r.path, r.name, r.role) for r in iter_model_refs(spec)]


def test_empty_spec_yields_nothing() -> None:
    assert _refs(FlowSpec()) == []
    assert _refs(FlowSpec(tasks=[FlowTask(name="t")])) == []


def test_string_task_name_yields_nothing() -> None:
    # A bare task-name string carries no model reference.
    assert _refs(FlowSpec(tasks=["inspect_evals/mmlu"])) == []


def test_live_task_model_and_roles_enumerated() -> None:
    # A live Task resolves its model/model_roles to live Model objects; those
    # models must still be counted, exactly as a live Model at FlowTask.model is.
    spec = FlowSpec(
        tasks=[Task(model="mockllm/model", model_roles={"grader": "mockllm/model"})]
    )
    assert _refs(spec) == [
        ("tasks[0].model", "mockllm/model", None),
        ("tasks[0].model_roles['grader']", "mockllm/model", "grader"),
    ]


def test_task_model_string() -> None:
    spec = FlowSpec(tasks=[FlowTask(model="openai/gpt-4o")])
    assert _refs(spec) == [("tasks[0].model", "openai/gpt-4o", None)]


def test_task_model_flow_model_name_and_default() -> None:
    # A FlowModel names up to two models: `name` and its `default` fallback.
    # Both must surface, as separate refs, so a host counts each.
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model=FlowModel(name="openai/gpt-4o", default="openai/gpt-4o-mini")
            )
        ]
    )
    assert _refs(spec) == [
        ("tasks[0].model", "openai/gpt-4o", None),
        ("tasks[0].model.default", "openai/gpt-4o-mini", None),
    ]


def test_flow_model_factory_only_has_no_name() -> None:
    def make() -> Model:
        return get_model("mockllm/model")

    spec = FlowSpec(tasks=[FlowTask(model=FlowModel(factory=make))])
    refs = list(iter_model_refs(spec))
    assert [(r.path, r.name, r.role) for r in refs] == [("tasks[0].model", None, None)]
    assert isinstance(refs[0], SpecModelRef)
    assert isinstance(refs[0].ref, FlowModel)


def test_string_factory_overrides_name() -> None:
    # _call_factory resolves a string factory ahead of `name`, so reporting
    # `name` here would let a caller declare an allowed model and run another.
    for factory in ("mockllm/effective", FlowFactory("mockllm/effective")):
        spec = FlowSpec(
            tasks=[FlowTask(model=FlowModel(name="mockllm/decoy", factory=factory))]
        )
        assert _refs(spec) == [("tasks[0].model", "mockllm/effective", None)]


def test_from_factory_flags_names_taken_from_factory() -> None:
    # For FlowModel a string factory IS the model id (it goes to
    # get_model(model=...)), so it is enumerable. But a host with a
    # no-factories policy must be able to spot it without unwrapping
    # FlowFactory itself.
    for factory in ("mockllm/effective", FlowFactory("mockllm/effective")):
        spec = FlowSpec(tasks=[FlowTask(model=FlowModel(factory=factory))])
        (ref,) = iter_model_refs(spec)
        assert (ref.name, ref.unenumerable, ref.from_factory) == (
            "mockllm/effective",
            False,
            True,
        )

    # A plain name is not factory-derived.
    spec = FlowSpec(tasks=[FlowTask(model=FlowModel(name="mockllm/model"))])
    (ref,) = iter_model_refs(spec)
    assert not ref.from_factory

    # A callable factory is both factory-derived and unenumerable.
    spec = FlowSpec(
        tasks=[FlowTask(model=FlowModel(factory=_module_level_model_factory))]
    )
    (ref,) = iter_model_refs(spec)
    assert ref.from_factory and ref.unenumerable


def test_callable_factory_suppresses_fields_it_ignores() -> None:
    # A callable factory returns the Model itself, so _create_model returns
    # before get_model and this FlowModel's default/role are dead — reporting
    # them would gate on models that cannot run. Its config is NOT dead:
    # apply_defaults hoists it into the task-level config, which governs
    # generation, so the fallback surfaces there (and only there).
    fm = FlowModel(
        factory=_module_level_model_factory,
        default="openai/never-runs",
        role="ignored",
        config=GenerateConfig(fallback_models=["claude-runs-via-task-config"]),
    )
    assert _refs(FlowSpec(tasks=[FlowTask(model=fm)])) == [
        ("tasks[0].model", None, None),
        ("tasks[0].config.fallback_models[0]", "claude-runs-via-task-config", None),
    ]

    # An explicit model_roles key is still the role the model is registered
    # under (_create_model_roles keys the mapping regardless), so it survives.
    # Role-model configs are not hoisted (only the default model's config is),
    # so no fallback ref appears here.
    assert _refs(FlowSpec(tasks=[FlowTask(model_roles={"grader": fm})])) == [
        ("tasks[0].model_roles['grader']", None, "grader")
    ]


def test_callable_factory_with_decoy_name_has_no_name() -> None:
    # A callable factory builds the model itself; `name` is never consulted, so
    # there is no statically enumerable name to report.
    def make() -> Model:
        return get_model("mockllm/model")

    spec = FlowSpec(
        tasks=[FlowTask(model=FlowModel(name="mockllm/decoy", factory=make))]
    )
    assert _refs(spec) == [("tasks[0].model", None, None)]


def test_live_model_role_is_preserved() -> None:
    # get_model(role=...) stores the role on the Model; it is a real binding.
    spec = FlowSpec(tasks=[FlowTask(model=get_model("mockllm/model", role="grader"))])
    assert _refs(spec) == [("tasks[0].model", "mockllm/model", "grader")]


def test_empty_model_roles_key_wins_over_model_role() -> None:
    # The mapping key wins even when falsy; only an absent key falls back.
    spec = FlowSpec(
        tasks=[FlowTask(model_roles={"": FlowModel(name="openai/x", role="other")})]
    )
    assert _refs(spec) == [("tasks[0].model_roles['']", "openai/x", "")]


def test_task_model_roles_carry_role() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model="openai/gpt-4o",
                model_roles={
                    "grader": "anthropic/claude-3-5-sonnet",
                    "red_team": FlowModel(name="openai/gpt-4o", default="openai/o1"),
                },
            )
        ]
    )
    assert _refs(spec) == [
        ("tasks[0].model", "openai/gpt-4o", None),
        ("tasks[0].model_roles['grader']", "anthropic/claude-3-5-sonnet", "grader"),
        ("tasks[0].model_roles['red_team']", "openai/gpt-4o", "red_team"),
        ("tasks[0].model_roles['red_team'].default", "openai/o1", "red_team"),
    ]


def test_flow_model_role_field_is_reported() -> None:
    # FlowModel.role is passed to get_model(role=...) at any model site, so a
    # role-bound model at task.model must not report role=None.
    spec = FlowSpec(tasks=[FlowTask(model=FlowModel(name="openai/x", role="grader"))])
    assert _refs(spec) == [("tasks[0].model", "openai/x", "grader")]


def test_model_roles_key_wins_over_flow_model_role() -> None:
    # The mapping key is the role the model is registered under for the task.
    spec = FlowSpec(
        tasks=[FlowTask(model_roles={"grader": FlowModel(name="openai/x", role="o")})]
    )
    assert _refs(spec) == [("tasks[0].model_roles['grader']", "openai/x", "grader")]


def test_live_model_name_is_qualified() -> None:
    spec = FlowSpec(tasks=[FlowTask(model=get_model("mockllm/model"))])
    refs = list(iter_model_refs(spec))
    assert [(r.path, r.name, r.role) for r in refs] == [
        ("tasks[0].model", "mockllm/model", None)
    ]


def test_defaults_merge_into_tasks_before_iteration() -> None:
    # Defaults are partial templates, not declarations: iteration happens on
    # the apply_defaults-merged spec, so their values are reported at the tasks
    # they actually land on — with the merged role and .default fallback.
    spec = FlowSpec(
        tasks=[
            FlowTask(name="t", model="openai/gpt-4o"),
            FlowTask(name="u", model="anthropic/claude-3-5-sonnet"),
        ],
        defaults=FlowDefaults(
            model=FlowModel(default="openai/gpt-4o-mini"),
            model_prefix={"anthropic/": FlowModel(role="special")},
        ),
    )
    assert _refs(spec) == [
        ("tasks[0].model", "openai/gpt-4o", None),
        ("tasks[0].model.default", "openai/gpt-4o-mini", None),
        ("tasks[1].model", "anthropic/claude-3-5-sonnet", "special"),
        ("tasks[1].model.default", "openai/gpt-4o-mini", "special"),
    ]


def test_defaults_model_name_shadowed_by_task_name() -> None:
    # A task's explicit model name wins over the defaults template's name; the
    # template name must not surface anywhere (it never runs for this task).
    spec = FlowSpec(
        tasks=[FlowTask(name="t", model="openai/explicit")],
        defaults=FlowDefaults(model=FlowModel(name="openai/from-defaults")),
    )
    assert _refs(spec) == [("tasks[0].model", "openai/explicit", None)]


def test_defaults_model_does_not_attach_to_modelless_task() -> None:
    # apply_defaults merges defaults.model only into an *existing* task.model;
    # a modelless task stays modelless (the ambient INSPECT_EVAL_MODEL applies
    # at run time), so no phantom ref is invented for it.
    spec = FlowSpec(
        tasks=[FlowTask(name="t")],
        defaults=FlowDefaults(model=FlowModel(name="openai/from-defaults")),
    )
    assert _refs(spec) == []


def test_defaults_on_taskless_spec_yield_nothing() -> None:
    # A defaults template with no task to land on configures nothing that
    # runs, so it produces no references.
    spec = FlowSpec(
        defaults=FlowDefaults(
            model=FlowModel(name="openai/gpt-4o", default="openai/gpt-4o-mini"),
            task=FlowTask(model_roles={"grader": "anthropic/claude-3-5-sonnet"}),
        )
    )
    assert _refs(spec) == []


def test_defaults_task_templates_merge_per_task() -> None:
    # defaults.task applies to every task; task_prefix only to name matches.
    # Bare-string tasks get the merged template too.
    spec = FlowSpec(
        tasks=["inspect_evals/mmlu", FlowTask(name="other/thing")],
        defaults=FlowDefaults(
            task=FlowTask(model="openai/gpt-4o"),
            task_prefix={
                "inspect_evals/": FlowTask(
                    model_roles={"grader": "anthropic/claude-3-5-sonnet"}
                )
            },
        ),
    )
    assert _refs(spec) == [
        ("tasks[0].model", "openai/gpt-4o", None),
        ("tasks[0].model_roles['grader']", "anthropic/claude-3-5-sonnet", "grader"),
        ("tasks[1].model", "openai/gpt-4o", None),
    ]


def test_scanner_model_and_roles() -> None:
    spec = FlowSpec(
        options=FlowOptions(
            scanner=ScannerConfig(
                scanners=["keyword_scanner"],
                model="openai/gpt-4o",
                model_roles={"grader": "anthropic/claude-3-5-sonnet"},
            )
        )
    )
    assert _refs(spec) == [
        ("options.scanner.model", "openai/gpt-4o", None),
        (
            "options.scanner.model_roles['grader']",
            "anthropic/claude-3-5-sonnet",
            "grader",
        ),
    ]


def test_scanner_model_non_str_shape_is_unenumerable() -> None:
    # ScannerConfig.model is typed Any. Only the documented str | Model shapes
    # are read; a list is reported as unenumerable rather than guessed at, since
    # over-reporting a name that never runs would trip a host's own gate.
    spec = FlowSpec.model_validate(
        {
            "tasks": [{"name": "t", "model": "mockllm/allowed"}],
            "options": {"scanner": {"scanners": [], "model": ["mockllm/other"]}},
        }
    )
    assert _refs(spec) == [
        ("tasks[0].model", "mockllm/allowed", None),
        ("options.scanner.model", None, None),
    ]


def test_scanner_model_comma_string_is_unenumerable() -> None:
    # resolve_models strips and uses only the first entry. Splitting here would
    # fabricate names that never run; reporting the composite would name a model
    # that does not exist. Neither guess nor pretend — flag it.
    spec = FlowSpec.model_validate(
        {"tasks": [], "options": {"scanner": {"scanners": [], "model": "a/x,b/y"}}}
    )
    (ref,) = iter_model_refs(spec)
    assert (ref.path, ref.name, ref.unenumerable) == (
        "options.scanner.model",
        None,
        True,
    )


def test_comma_string_outside_scanner_model_is_a_plain_name() -> None:
    # Only resolve_models (scanner.model) comma-splits. get_model does not, and
    # neither does resolve_model_roles, so a comma there is one (bad) name.
    spec = FlowSpec(tasks=[FlowTask(model="a/x,b/y")])
    assert _refs(spec) == [("tasks[0].model", "a/x,b/y", None)]
    spec = FlowSpec.model_validate(
        {
            "tasks": [],
            "options": {
                "scanner": {"scanners": [], "model_roles": {"grader": "a/x,b/y"}}
            },
        }
    )
    assert _refs(spec) == [
        ("options.scanner.model_roles['grader']", "a/x,b/y", "grader")
    ]


def test_flow_model_at_scanner_site_is_unenumerable() -> None:
    # ScannerConfig.model is `Any`, so a FlowModel can be put there in Python —
    # but resolve_models/resolve_model_roles only take `str | Model | None` and
    # raise on a FlowModel. Naming it would claim a model that cannot run, the
    # same over-report the comma-string branch avoids.
    spec = FlowSpec(
        options=FlowOptions(
            scanner=ScannerConfig(
                scanners=["keyword_scanner"],
                model=FlowModel(name="openai/never-runs"),
                model_roles={"grader": FlowModel(name="openai/also-never-runs")},
            )
        )
    )
    assert _refs(spec) == [
        ("options.scanner.model", None, None),
        ("options.scanner.model_roles['grader']", None, "grader"),
    ]
    assert all(r.unenumerable for r in iter_model_refs(spec))


def test_none_scanner_role_is_unenumerable_but_none_model_is_absence() -> None:
    # resolve_model_roles calls _set_role on the value, so {"grader": None} is a
    # declared role that raises at scan time — an unusable site the host should
    # be able to reject, not silence. resolve_models treats a None model as "no
    # model" and falls back to the ambient one, so that really is absence.
    spec = FlowSpec.model_validate(
        {
            "tasks": [],
            "options": {
                "scanner": {"scanners": [], "model": None, "model_roles": {"g": None}}
            },
        }
    )
    assert _refs(spec) == [("options.scanner.model_roles['g']", None, "g")]
    assert all(r.unenumerable for r in iter_model_refs(spec))

    # An absent role mapping stays silent — nothing was declared.
    spec = FlowSpec.model_validate(
        {"tasks": [], "options": {"scanner": {"scanners": [], "model_roles": None}}}
    )
    assert _refs(spec) == []


def test_scanner_model_roles_non_str_shape_is_unenumerable() -> None:
    # Role values go through resolve_model_roles (get_model on the whole value),
    # which accepts neither lists nor comma strings.
    spec = FlowSpec.model_validate(
        {
            "tasks": [],
            "options": {
                "scanner": {"scanners": [], "model_roles": {"grader": ["a/x"]}}
            },
        }
    )
    assert _refs(spec) == [("options.scanner.model_roles['grader']", None, "grader")]


def test_scanner_as_file_path_is_unenumerable() -> None:
    # A scanner given as a config-file path is loaded at eval time; its models
    # are real but unreadable here, so surface an unenumerable ref rather than
    # nothing, letting a host's "name is None -> reject" policy fire.
    spec = FlowSpec(options=FlowOptions(scanner="./scan.yaml"))
    assert _refs(spec) == [("options.scanner", None, None)]


def test_unreadable_scanner_model_is_unenumerable() -> None:
    # An Any-typed field holding a shape we cannot read must fail closed.
    spec = FlowSpec.model_validate(
        {"tasks": [], "options": {"scanner": {"scanners": [], "model": {"a": 1}}}}
    )
    assert _refs(spec) == [("options.scanner.model", None, None)]


def test_task_config_fallback_models() -> None:
    # GenerateConfig.fallback_models name real models that handle requests after
    # a classifier refusal, so they must be counted like any other model.
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model="openai/gpt-4o",
                config=GenerateConfig(
                    fallback_models=["claude-opus-4-5", "claude-sonnet-4-5"]
                ),
            )
        ]
    )
    assert _refs(spec) == [
        ("tasks[0].model", "openai/gpt-4o", None),
        ("tasks[0].config.fallback_models[0]", "claude-opus-4-5", None),
        ("tasks[0].config.fallback_models[1]", "claude-sonnet-4-5", None),
    ]


def test_flow_model_config_fallback_inherits_role() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model_roles={
                    "grader": FlowModel(
                        name="openai/gpt-4o",
                        config=GenerateConfig(fallback_models=["claude-fb"]),
                    )
                }
            )
        ]
    )
    assert _refs(spec) == [
        ("tasks[0].model_roles['grader']", "openai/gpt-4o", "grader"),
        (
            "tasks[0].model_roles['grader'].config.fallback_models[0]",
            "claude-fb",
            "grader",
        ),
    ]


def test_defaults_config_fallback_models_merge_per_task() -> None:
    # defaults.config merges into each task's config, so its fallbacks are
    # reported once per task they govern — and never for a taskless spec.
    spec = FlowSpec(
        tasks=[FlowTask(name="a"), FlowTask(name="b")],
        defaults=FlowDefaults(config=GenerateConfig(fallback_models=["claude-fb"])),
    )
    assert _refs(spec) == [
        ("tasks[0].config.fallback_models[0]", "claude-fb", None),
        ("tasks[1].config.fallback_models[0]", "claude-fb", None),
    ]
    assert (
        _refs(
            FlowSpec(
                defaults=FlowDefaults(config=GenerateConfig(fallback_models=["x"]))
            )
        )
        == []
    )


def test_scanner_generate_config_fallback_models() -> None:
    spec = FlowSpec(
        options=FlowOptions(
            scanner=ScannerConfig(
                scanners=["keyword_scanner"],
                model="openai/gpt-4o",
                generate_config=GenerateConfig(fallback_models=["claude-fb"]),
            )
        )
    )
    assert _refs(spec) == [
        ("options.scanner.model", "openai/gpt-4o", None),
        ("options.scanner.generate_config.fallback_models[0]", "claude-fb", None),
    ]


def test_live_task_config_fallback_models() -> None:
    spec = FlowSpec(tasks=[Task(config=GenerateConfig(fallback_models=["claude-fb"]))])
    assert _refs(spec) == [
        ("tasks[0].config.fallback_models[0]", "claude-fb", None),
    ]


def test_live_model_config_fallback_models() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model=get_model(
                    "mockllm/model",
                    config=GenerateConfig(fallback_models=["claude-fb"]),
                )
            )
        ]
    )
    # apply_defaults hoists the default model's config into task.config, so
    # the same fallback appears at both post-merge locations. Same name, so a
    # name-set consumer is unaffected.
    assert _refs(spec) == [
        ("tasks[0].model", "mockllm/model", None),
        ("tasks[0].model.config.fallback_models[0]", "claude-fb", None),
        ("tasks[0].config.fallback_models[0]", "claude-fb", None),
    ]


def test_fallback_models_survive_json_roundtrip() -> None:
    # Hawk ships resolved specs as JSON. FlowTask.config is typed GenerateConfig
    # (reloads as GenerateConfig), but ScannerConfig.generate_config is typed
    # Any, so it reloads as a plain dict — the walk must still find its
    # fallback_models, or a scanner's fallback model escapes the access-control
    # set on exactly the wire path this API exists to protect.
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model="openai/gpt-4o",
                config=GenerateConfig(fallback_models=["claude-task-fb"]),
            )
        ],
        options=FlowOptions(
            scanner=ScannerConfig(
                scanners=["keyword_scanner"],
                model="openai/gpt-4o",
                generate_config=GenerateConfig(fallback_models=["claude-scan-fb"]),
            )
        ),
    )
    reloaded = FlowSpec.model_validate(model_dump(spec))
    assert _refs(reloaded) == [
        ("tasks[0].model", "openai/gpt-4o", None),
        ("tasks[0].config.fallback_models[0]", "claude-task-fb", None),
        ("options.scanner.model", "openai/gpt-4o", None),
        (
            "options.scanner.generate_config.fallback_models[0]",
            "claude-scan-fb",
            None,
        ),
    ]


def test_stable_order_across_whole_spec() -> None:
    # Tasks first, then options. (Defaults merge into tasks, so a default
    # model surfaces in the task leg, not a leg of its own.)
    spec = FlowSpec(
        tasks=[FlowTask(name="t"), FlowTask(model="a/task-model")],
        defaults=FlowDefaults(task=FlowTask(model="a/default-model")),
        options=FlowOptions(
            scanner=ScannerConfig(scanners=["keyword_scanner"], model="a/scanner-model")
        ),
    )
    assert [r.name for r in iter_model_refs(spec)] == [
        "a/default-model",
        "a/task-model",
        "a/scanner-model",
    ]


def test_hawk_style_consumption() -> None:
    # The two things a host derives: the set of model names (for permission
    # checks / log ACL) and the FlowModel objects (for api_key scrubbing).
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model=FlowModel(name="openai/gpt-4o", default="openai/gpt-4o-mini"),
                model_roles={"grader": "anthropic/claude-3-5-sonnet"},
            )
        ]
    )
    names = {r.name for r in iter_model_refs(spec) if r.name}
    assert names == {
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "anthropic/claude-3-5-sonnet",
    }
    flow_models = [r.ref for r in iter_model_refs(spec) if isinstance(r.ref, FlowModel)]
    assert len(flow_models) == 1


def test_defaults_field_templates_merge_rather_than_surface() -> None:
    # The documented defaults pattern (examples/flow_defaults.py): a FlowModel
    # carrying only field defaults is a partial template, not a declaration.
    # Iteration happens after apply_defaults, so the template's fields land on
    # each task's (named) model instead of surfacing as a nameless ref a host
    # might mistakenly reject.
    spec = FlowSpec(
        tasks=[FlowTask(name="t", model="openai/gpt-4o")],
        defaults=FlowDefaults(
            model=FlowModel(model_args={"arg": "foo"}),
            model_prefix={"openai/": FlowModel(config=GenerateConfig(temperature=1))},
        ),
    )
    (ref,) = iter_model_refs(spec)
    assert (ref.path, ref.name, ref.unenumerable) == (
        "tasks[0].model",
        "openai/gpt-4o",
        False,
    )
    assert isinstance(ref.ref, FlowModel)
    assert ref.ref.model_args == {"arg": "foo"}


def test_nameless_task_model_is_not_unenumerable() -> None:
    # A task-level FlowModel with neither name nor factory declares no model;
    # instantiation rejects it ("Model name is required") rather than running
    # anything, so it is nameless but not unenumerable — nothing binds.
    spec = FlowSpec(tasks=[FlowTask(model=FlowModel(model_args={"a": 1}))])
    (ref,) = iter_model_refs(spec)
    assert (ref.name, ref.unenumerable) == (None, False)


def test_unenumerable_marks_only_bound_but_unknowable_models() -> None:
    def make() -> Model:
        return get_model("mockllm/model")

    # A callable factory binds a model whose name cannot be known statically.
    spec = FlowSpec(tasks=[FlowTask(model=FlowModel(factory=make))])
    (ref,) = iter_model_refs(spec)
    assert ref.name is None and ref.unenumerable

    # Same via FlowFactory wrapping a callable.
    spec = FlowSpec(tasks=[FlowTask(model=FlowModel(factory=FlowFactory(make)))])
    (ref,) = iter_model_refs(spec)
    assert ref.name is None and ref.unenumerable

    # An unreadable site is unenumerable too.
    spec = FlowSpec(options=FlowOptions(scanner="./scan.yaml"))
    (ref,) = iter_model_refs(spec)
    assert ref.name is None and ref.unenumerable

    # A named model is enumerable.
    spec = FlowSpec(tasks=[FlowTask(model="openai/gpt-4o")])
    (ref,) = iter_model_refs(spec)
    assert not ref.unenumerable


def test_unexpanded_includes_raise() -> None:
    # Includes reference other spec files, which cannot be read here, so an
    # unresolved spec is rejected eagerly (not on first iteration) rather than
    # silently under-reporting.
    spec = FlowSpec(includes=[FlowSpec(tasks=[FlowTask(model="openai/gpt-4o")])])
    with pytest.raises(ValueError, match="unexpanded includes"):
        iter_model_refs(spec)


def test_kind_discriminates_reference_namespaces() -> None:
    # fallback_models entries are provider-native ids, not `provider/model`
    # references. A host must be able to tell them apart without parsing paths.
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model=FlowModel(
                    name="anthropic/claude-opus-4-5",
                    default="anthropic/claude-sonnet-4-5",
                    config=GenerateConfig(fallback_models=["claude-haiku-4-5"]),
                )
            )
        ]
    )
    assert [(r.path, r.kind) for r in iter_model_refs(spec)] == [
        ("tasks[0].model", "model"),
        ("tasks[0].model.default", "default"),
        ("tasks[0].model.config.fallback_models[0]", "fallback"),
        # apply_defaults hoists the model's config into task.config too.
        ("tasks[0].config.fallback_models[0]", "fallback"),
    ]
    # The Inspect-namespaced subset a host authorizes by `provider/model`.
    assert {r.name for r in iter_model_refs(spec) if r.kind != "fallback"} == {
        "anthropic/claude-opus-4-5",
        "anthropic/claude-sonnet-4-5",
    }


def test_unenumerable_ref_kind() -> None:
    spec = FlowSpec(options=FlowOptions(scanner="./scan.yaml"))
    (ref,) = iter_model_refs(spec)
    assert ref.kind == "model" and ref.unenumerable


def test_walk_over_loaded_spec(tmp_path: Path) -> None:
    # Integration through the public loader: defaults are merged into tasks and
    # `defaults` is cleared, so the walk sees a different shape than in-memory.
    config = tmp_path / "flow.yml"
    config.write_text(
        "tasks:\n"
        "  - name: t\n"
        "    model: openai/gpt-4o\n"
        "defaults:\n"
        "  model:\n"
        "    default: openai/gpt-4o-mini\n"
    )
    spec = load_spec(str(config))
    assert {r.name for r in iter_model_refs(spec)} == {
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
    }


def _module_level_model_factory() -> Model:
    return get_model("mockllm/model")


def test_callable_factory_becomes_a_name_once_serialized() -> None:
    # Flow serializes a callable factory to a "file.py@attr" string, which
    # reloads as a *string* factory. unenumerable is therefore in-process only;
    # on the wire the ref reports the name _call_factory will resolve.
    spec = FlowSpec(
        tasks=[FlowTask(model=FlowModel(factory=_module_level_model_factory))]
    )
    (ref,) = iter_model_refs(spec)
    assert ref.name is None and ref.unenumerable

    reloaded = FlowSpec.model_validate(model_dump(spec))
    (ref,) = iter_model_refs(reloaded)
    assert ref.name is not None
    assert ref.name.endswith("@_module_level_model_factory")
    assert not ref.unenumerable


def test_refs_dedup_by_name_not_by_ref() -> None:
    # Refs are unhashable on purpose: `ref` can be a mutable FlowModel, so a
    # hash derived from it would go stale if the spec were edited. Deduplicate
    # on names, which is what a host actually wants.
    spec = FlowSpec(
        tasks=[
            FlowTask(model="openai/gpt-4o"),
            FlowTask(model=FlowModel(name="openai/gpt-4o")),
            FlowTask(model=get_model("mockllm/model")),
        ]
    )
    refs = list(iter_model_refs(spec))
    assert {r.name for r in refs} == {"openai/gpt-4o", "mockllm/model"}
    with pytest.raises(TypeError):
        set(refs)

    # Unhashable for *every* ref shape, not just the one holding a FlowModel —
    # otherwise hashability would depend on what the spec happens to contain.
    assert SpecModelRef.__hash__ is None
    for ref in ("openai/gpt-4o", None, FlowModel(name="openai/gpt-4o")):
        with pytest.raises(TypeError):
            hash(SpecModelRef("tasks[0].model", ref))


def _model_candidates(value: object, path: str, under_model_field: bool) -> list[str]:
    """Paths that *look* like model references, found without naming any field.

    Companion to the field-name snapshot: that guard pins Flow's own types, so it
    is blind to a model field appearing on an inspect-ai type. This one discovers
    by traversing values, so it sees those too.
    """
    if isinstance(value, Model):
        # A live Model is not a pydantic model — nothing to descend into.
        return [path]
    if under_model_field and isinstance(value, str):
        return [path]
    # A FlowModel is itself a reference *and* has fields worth descending into.
    found: list[str] = [path] if isinstance(value, FlowModel) else []
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            if name in value.model_fields_set:
                found += _model_candidates(
                    getattr(value, name), f"{path}.{name}", "model" in name.lower()
                )
    elif isinstance(value, Mapping):
        for key, item in value.items():
            found += _model_candidates(
                item,
                f"{path}[{key!r}]",
                under_model_field or "model" in str(key).lower(),
            )
    elif isinstance(value, Sequence) and not isinstance(value, str):
        for index, item in enumerate(value):
            found += _model_candidates(item, f"{path}[{index}]", under_model_field)
    return found


def test_no_model_shaped_value_escapes_unclassified() -> None:
    # Traverses the spec generically and asserts every model-shaped value is
    # either yielded by iter_model_refs or listed below. Unlike the field-name
    # snapshot, this would fire if inspect-ai added a model field to
    # ScannerConfig or GenerateConfig — the gap the snapshot cannot cover.
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="t",
                model=FlowModel(
                    name="openai/a",
                    default="openai/b",
                    config=GenerateConfig(fallback_models=["claude-x"]),
                ),
                model_roles={"grader": "openai/c"},
                config=GenerateConfig(fallback_models=["claude-y"]),
                args={"grader_model": "openai/in-args"},
                extra_args=FlowExtraArgs(model={"api_key": "secret"}),
            ),
            Task(model="mockllm/model", model_roles={"g": "mockllm/model"}),
        ],
        defaults=FlowDefaults(
            model=FlowModel(name="openai/d"),
            model_prefix={"openai/": FlowModel(name="openai/e")},
            config=GenerateConfig(fallback_models=["claude-z"]),
        ),
        options=FlowOptions(
            scanner=ScannerConfig(
                scanners=["keyword_scanner"],
                model="openai/f",
                model_roles={"r": "openai/g"},
                generate_config=GenerateConfig(fallback_models=["claude-w"]),
            )
        ),
    )
    walked = {r.path for r in iter_model_refs(spec)}
    # iter_model_refs walks the defaults-merged spec, so the oracle must
    # traverse the same shape or its paths would name pre-merge locations.
    candidates = {
        c.lstrip(".") for c in _model_candidates(apply_defaults(spec), "", False)
    }
    assert candidates - walked == {
        # Free-form constructor args and model-construction kwargs are both
        # documented scope exclusions. The second is why a generic walk cannot
        # replace the hand-written one: it reports an api key as a model.
        "tasks[0].args['grader_model']",
        "tasks[0].extra_args.model['api_key']",
    }
    # The converse gap is expected — this is why the oracle complements the
    # hand-written walk rather than replacing it. A live Task is not a pydantic
    # model, so nothing generic reaches the models inside it; and `default` is
    # not a *model*-named field, so a name heuristic cannot discover it either.
    assert walked - candidates == {
        "tasks[1].model",
        "tasks[1].model_roles['g']",
        "tasks[0].model.default",
    }


def test_spec_fields_are_classified_for_models() -> None:
    # #785 deleted its equivalent of this test, because deriving
    # portability from the real serializer made it unnecessary. No such oracle
    # exists for "is this field a model reference" (see the design doc), so this
    # walk is hand-written and this guard is what keeps it from silently falling
    # behind the schema. Don't remove it for parity with test_portable.py.
    #
    # If this test fails, you added or renamed a field on a spec type. Decide
    # whether the field can carry a model reference:
    #
    # FlowDefaults is deliberately NOT pinned: iteration happens on the
    # apply_defaults-merged spec, so a new defaults field is defaults.py's
    # concern — the walk and the runner share that exact merge code, and a
    # field apply_defaults ignores does nothing at runtime either.
    #   - if it can, extend iter_model_refs in
    #     src/inspect_flow/_config/model_refs.py (and the coverage list in
    #     design/model_reference_introspection.md), then update the snapshot;
    #   - if it cannot, just update the snapshot.
    # Among FlowOptions, only `scanner` carries model references today.
    # `model_cost_config` is keyed by model name but is pricing metadata —
    # nothing generates because of it, so counting it would over-report. The
    # scanner's own model fields and GenerateConfig.fallback_models live on
    # inspect-ai types (ScannerConfig, GenerateConfig), which are deliberately
    # not snapshotted here (pinning an external type's fields is fragile against
    # inspect-ai refactors).
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
        "headline_metric",
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
    # FlowAgent/FlowSolver/FlowScorer carry no model field today, but they are
    # reachable model-container candidates (via defaults.agent/solver and
    # FlowTask.solver/scorer), so pin them too: a future `model` field on one
    # must fail this test rather than silently escape iter_model_refs.
    assert sorted(FlowAgent.model_fields) == [
        "args",
        "factory",
        "flow_metadata",
        "name",
        "type",
    ]
    assert sorted(FlowSolver.model_fields) == [
        "args",
        "factory",
        "flow_metadata",
        "name",
    ]
    assert sorted(FlowScorer.model_fields) == [
        "args",
        "factory",
        "flow_metadata",
        "name",
    ]
    # FlowExtraArgs.model is model-*creation* args, not a model reference (it is
    # merged into the get_model call), so it is not walked. Pinned because it is
    # the most plausible place a future real reference would land.
    assert sorted(FlowExtraArgs.model_fields) == [
        "agent",
        "model",
        "scorer",
        "solver",
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
        "sandbox_prebuilt",
        "scanner",
        "score",
        "score_display",
        "score_on_error",
        "tags",
        "trace",
    ]
