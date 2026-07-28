from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Literal

from inspect_ai import ScannerConfig, Task
from inspect_ai.model import GenerateConfig, Model

from inspect_flow._types.flow_types import (
    FlowFactory,
    FlowModel,
    FlowSpec,
    FlowTask,
    NotGiven,
)
from inspect_flow._util.not_given import default_none, is_set


# Not `frozen=True`: that generates a `__hash__`, and `ref` may be a mutable
# `FlowModel`, so the hash would go stale whenever the spec is edited — silently
# breaking set membership — and would raise only for *some* refs, making
# hashability depend on what `ref` happens to hold. A plain `eq=True` dataclass
# is unhashable outright, which is the honest contract here. Deduplicate on names
# instead: `{r.name for r in refs}`. This reversed twice under review; see
# design/model_reference_introspection.md before changing it back.
@dataclass
class SpecModelRef:
    """A single model reference found in a flow spec."""

    path: str
    """Field path of the reference (e.g. `"tasks[0].model_roles['grader']"`)."""

    ref: str | FlowModel | Model | None
    """The reference as it appears in the spec: a model name string, a `FlowModel`,
    or an already-instantiated `Model`. `None` marks a model site that exists but
    cannot be read statically (e.g. a scanner given as a config-file path)."""

    role: str | None = None
    """The named role this reference is bound to, or `None` for an unroled model.

    Taken from the `model_roles` key, falling back to `FlowModel.role` (which is
    passed to `get_model(role=...)` at any model site); the mapping key wins when
    both are set.

    This records how the reference is *declared*, not which slot the model will
    end up serving. So a `kind="fallback"` ref is roled only when it comes from a
    `FlowModel`'s own `config` — that config is an argument to the same
    `get_model` call that binds the role. A fallback declared on a `FlowTask` or
    `defaults` `config` is always `None`: those are task/run-level generate
    configs (`FlowTask.config` explicitly "does not apply to model roles"), and
    no role participates at that layer. `defaults.config` shows why this cannot
    be derived — one declaration there may serve several models in different
    roles, or a modelless task with no role at all."""

    kind: Literal["model", "default", "fallback"] = "model"
    """Which kind of reference this is, and hence which namespace `name` is in.

    `"model"` and `"default"` (a `FlowModel.default`) are Inspect
    `provider/model` references. `"fallback"` is a `GenerateConfig.fallback_models`
    entry, which is a provider-native id with no provider prefix. A host
    comparing or authorizing names across both must branch on this rather than
    parse `path`."""

    @property
    def name(self) -> str | None:
        """The model name that will actually be used, or `None` if not static.

        A `FlowModel`'s string `factory` takes precedence over `name`, so it is
        reported instead — unlike other Flow types, that string is not a factory
        registry reference but the model id itself, passed to
        `get_model(model=...)` (see `from_factory`). A callable `factory` builds
        the model itself and yields `None` even when `name` is set. A live
        `Model` reports its provider-qualified name.

        `None` has two causes, distinguished by `unenumerable`: either a model
        binds here but its name cannot be known statically, or the reference
        declares no model at all (a `FlowModel` carrying only field defaults,
        as in `defaults.model`). Key policy on `unenumerable` rather than on
        this — and note `unenumerable` is not by itself sufficient: a *string*
        `factory` is enumerable but its name is a factory id, so a host feeding
        `name` to a model lookup should check `from_factory` too.

        Names are Inspect `provider/model` references, except entries from
        `GenerateConfig.fallback_models`, which are provider-native ids passed
        verbatim to the provider (e.g. `"claude-opus-4-5"`).

        A model reached through a `base_url` override still reports its Inspect
        id, which is an assertion about identity rather than a guarantee of
        which endpoint serves the request.
        """
        if self.ref is None:
            return None
        if isinstance(self.ref, str):
            return self.ref
        if isinstance(self.ref, Model):
            return str(self.ref)
        factory = _effective_factory(self.ref)
        if factory is not None:
            return factory if isinstance(factory, str) else None
        return default_none(self.ref.name)

    @property
    def from_factory(self) -> bool:
        """Whether `name` came from `FlowModel.factory` rather than `name`.

        For a `FlowModel` a string `factory` *is* the model id — it is passed to
        `get_model(model=...)`, and inspect has no separate model-factory
        registry — so such a ref is still enumerable. But `factory` means
        "registry name" on every other Flow type, and a host may have its own
        policy against factories; this reports one without making the caller
        unwrap `FlowFactory` and re-derive the precedence rule.
        """
        return (
            isinstance(self.ref, FlowModel) and _effective_factory(self.ref) is not None
        )

    @property
    def unenumerable(self) -> bool:
        """Whether a model binds here whose name is not statically knowable.

        `True` for a model site this walk cannot read (`ref is None`) and for a
        `FlowModel` built by a callable `factory`. `False` when `name` is `None`
        merely because the reference declares no model — a `FlowModel` carrying
        only field defaults, which is the documented `defaults.model` pattern.

        This is the signal for "I cannot name the model", and a host that
        cannot allow what it cannot name should reject specs where this is
        `True`, without rejecting ordinary field-default templates. It is not
        the only thing a host may want to reject: see `from_factory` for names
        that are known but derived from `FlowModel.factory`.

        Note a callable factory is only `True` in-process: serializing a spec
        rewrites it to a `file.py@attr` string, which reloads as a string
        factory and is reported as a name (the name `_call_factory` will then
        resolve). Such a name is not a `provider/model` reference, so it fails
        an allow-list rather than passing one.
        """
        if self.ref is None:
            return True
        if isinstance(self.ref, FlowModel):
            return callable(_effective_factory(self.ref))
        return False


def _effective_factory(model: FlowModel) -> Callable[..., Model] | str | None:
    """The factory that decides the model, unwrapped from any `FlowFactory`."""
    factory = default_none(model.factory)
    return factory.factory if isinstance(factory, FlowFactory) else factory


def iter_model_refs(spec: FlowSpec) -> Iterator[SpecModelRef]:
    """Yield the model references declared in a flow spec.

    Order is stable: `includes`, then tasks, then `defaults`, then `options`.

    Walks the whole spec — task `model` and `model_roles` (whether a task is a
    `FlowTask` or an already-instantiated `Task`), `defaults.model` and
    `defaults.model_prefix`, the `defaults.task` / `defaults.task_prefix`
    templates, and `options.scanner` — and yields one `SpecModelRef` per
    reference. A `FlowModel`'s `default` fallback is yielded as its own
    reference at `<path>.default`: it is a declared reference naming a distinct
    model, enumerated because the field is still in the schema even though Flow
    does not currently bind it (issue #778, which will likely remove the field —
    this handling retires with it). Likewise every
    `GenerateConfig.fallback_models` entry (on a task, model, `defaults.config`,
    or scanner) is yielded at `<config>.fallback_models[i]`, because those models
    handle requests after a classifier refusal.

    Nothing is resolved, instantiated, expanded, or installed. Specs pulled in
    via `includes` are not descended into — iterate a resolved spec (the loader
    clears `includes` once merged); an unresolved spec yields one unenumerable
    ref per include rather than silently under-reporting.

    **This will not find every model a run may use.** It reads the model
    reference fields Flow declares in its own schema; it does not execute
    anything, so any model chosen at run time is invisible to it:

    - **user code** — a callable `factory` or an `@after_instantiate` hook can
      return any model, including one named nowhere in the spec;
    - **ambient configuration** — a task or scanner with no model resolves
      `INSPECT_EVAL_MODEL` / `SCOUT_SCAN_MODEL` from the environment, which
      `spec.env` may itself set;
    - **free-form constructor args** — most commonly a plain string consumed by
      user code (`FlowTask(args={"grader_model": "openai/gpt-4o"})`, a
      `model_graded_qa` scorer's `model` arg); also any
      `{"model": ..., "config": ...}` mapping, which inspect-ai materializes
      into a live model, api key included.

    An empty or short result therefore does not prove which models will run.
    What it does guarantee is that no *declared* spec field is missed as Flow's
    schema grows: a snapshot test forces every new field on the model-bearing
    spec types through this classification.

    Where a declared model site exists but cannot be read statically (e.g. a
    scanner given as a config-file path, or an `Any`-typed field holding an
    unrecognized shape), a `SpecModelRef` is yielded with `unenumerable` set
    rather than nothing. A host applying policy should reject what it cannot
    enumerate — refs where `unenumerable` is `True`, and (if it does not permit
    factories) where `from_factory` is `True`, plus model-bearing constructor
    args and modelless tasks, which are outside this walk — then apply policy
    over what this yields.

    Args:
        spec: The flow spec to introspect.

    Yields:
        Each model reference with its field path and binding role.
    """
    for index, _ in enumerate(spec.includes or []):
        # Includes are expanded at load time (the loader clears this field), so
        # a spec that still has them is unresolved and under-reports.
        yield SpecModelRef(f"includes[{index}]", None)
    for index, task in enumerate(spec.tasks or []):
        if isinstance(task, (FlowTask, Task)):
            yield from _task_model_refs(task, f"tasks[{index}]")
    defaults = default_none(spec.defaults)
    if defaults:
        yield from _fallback_model_refs(defaults.config, "defaults.config")
        yield from _model_refs(defaults.model, "defaults.model")
        for key, model in (default_none(defaults.model_prefix) or {}).items():
            yield from _model_refs(model, f"defaults.model_prefix[{key!r}]")
        if is_set(defaults.task):
            yield from _task_model_refs(defaults.task, "defaults.task")
        for key, template in (default_none(defaults.task_prefix) or {}).items():
            yield from _task_model_refs(template, f"defaults.task_prefix[{key!r}]")
    yield from _scanner_model_refs(spec)


def _task_model_refs(task: FlowTask | Task, path: str) -> Iterator[SpecModelRef]:
    yield from _model_and_role_refs(task.model, task.model_roles, path)
    yield from _fallback_model_refs(task.config, f"{path}.config")


def _scanner_model_refs(spec: FlowSpec) -> Iterator[SpecModelRef]:
    options = default_none(spec.options)
    scanner = default_none(options.scanner) if options else None
    if scanner is None:
        return
    if not isinstance(scanner, ScannerConfig):
        # A scanner given as a config-file path is loaded at eval time; its
        # models are real but unreadable here, so fail closed.
        yield SpecModelRef("options.scanner", None)
        return
    yield from _scanner_site_refs(
        scanner.model, "options.scanner.model", via_resolve_models=True
    )
    for role, value in (scanner.model_roles or {}).items():
        yield from _scanner_site_refs(
            value, f"options.scanner.model_roles[{role!r}]", role
        )
    # Path names the logical field even when `generate_config` round-trips as a
    # plain mapping, so this stays `...generate_config.fallback_models[i]` rather
    # than switching to `['fallback_models']` subscripting by runtime shape.
    yield from _fallback_model_refs(
        scanner.generate_config, "options.scanner.generate_config"
    )


def _scanner_site_refs(
    value: object, path: str, role: str | None = None, via_resolve_models: bool = False
) -> Iterator[SpecModelRef]:
    """Model refs at an `Any`-typed scanner field.

    Both fields accept only `str | Model | None` — notably *not* a `FlowModel`,
    which raises at scan time. Anything else is reported unenumerable rather
    than named, so the walk never claims a model that cannot run.

    `via_resolve_models` marks `scanner.model`, the one field handled by
    `resolve_models`; role values go through `resolve_model_roles`. They differ
    in both respects that matter here:

    - **Commas.** `resolve_models` strips and splits on them (scout then keeps
      entry `[0]`). Replicating that normalization would drift, and reporting
      the whole string would name a model that does not exist, so it is
      unenumerable instead. Surrounding whitespace is *not* stripped for the
      same reason — an unstripped name errs safe, failing an allow-list rather
      than passing one. `resolve_model_roles` does not split, so a comma in a
      role value is genuinely one (bad) name.
    - **`None`.** The scan plumbing drops a `None` `scanner.model` before it is
      forwarded, making it indistinguishable from unset, and scout then falls
      back to `SCOUT_SCAN_MODEL` — so it is a real absence. (Not because
      `resolve_models` tolerates it: called directly it would return a
      `none/none` NoModel.) `resolve_model_roles` has no such guard — it calls
      `_set_role` on the value and raises — so `{"grader": None}` is a
      *declared* role that cannot run, an unenumerable site rather than an
      absent one. An absent key stays silent: only present keys are iterated.
    """
    if value is None:
        if via_resolve_models:
            return
        yield SpecModelRef(path, None, role)
    elif via_resolve_models and isinstance(value, str) and "," in value:
        yield SpecModelRef(path, None, role)
    elif isinstance(value, (str, Model)):
        yield from _model_refs(value, path, role)
    else:
        yield SpecModelRef(path, None, role)


def _model_and_role_refs(
    model: object,
    model_roles: Mapping[str, object] | None | NotGiven,
    path: str,
) -> Iterator[SpecModelRef]:
    yield from _model_refs(model, f"{path}.model")
    for role, value in (default_none(model_roles) or {}).items():
        yield from _model_refs(value, f"{path}.model_roles[{role!r}]", role)


def _model_refs(
    ref: object, path: str, role: str | None = None
) -> Iterator[SpecModelRef]:
    if ref is None or isinstance(ref, NotGiven):
        return
    if not isinstance(ref, (str, FlowModel, Model)):
        # A model site holding a value we cannot read must fail closed: emit an
        # unenumerable ref so a host's "name is None -> reject" policy fires.
        yield SpecModelRef(path, None, role)
        return
    # A callable `factory` returns the Model itself, so `_create_model` returns
    # before `get_model`, and this FlowModel's `default`, `config`, and `role`
    # are never applied. Reporting them would name models that cannot run.
    built_by_callable = isinstance(ref, FlowModel) and callable(_effective_factory(ref))
    if role is None and not isinstance(ref, str) and not built_by_callable:
        # A model outside model_roles can still bind a role: FlowModel.role is
        # passed to get_model(role=...), and a live Model carries the role it
        # was created with. Only an absent mapping key falls back to it.
        role = default_none(ref.role)
    yield SpecModelRef(path, ref, role)
    if built_by_callable:
        return
    if isinstance(ref, FlowModel) and is_set(ref.default):
        yield SpecModelRef(f"{path}.default", ref.default, role, "default")
    if not isinstance(ref, str):
        yield from _fallback_model_refs(ref.config, f"{path}.config", role)


def _fallback_model_refs(
    config: object, path: str, role: str | None = None
) -> Iterator[SpecModelRef]:
    # `GenerateConfig`-typed fields reload as `GenerateConfig`, but a config on
    # an `Any`-typed field (e.g. `ScannerConfig.generate_config`) survives a
    # YAML/JSON round-trip as a plain mapping, so handle both.
    if isinstance(config, GenerateConfig):
        fallbacks = config.fallback_models
    elif isinstance(config, Mapping):
        fallbacks = config.get("fallback_models")
    else:
        return
    if not isinstance(fallbacks, (list, tuple)):
        return
    for index, name in enumerate(fallbacks):
        if isinstance(name, str):
            yield SpecModelRef(
                f"{path}.fallback_models[{index}]", name, role, "fallback"
            )
