# Model-reference introspection

## Problem

Platforms like METR's Hawk need the set of models a `FlowSpec` **declares**. Not to enforce model access — the model gateway authorizes every call at request time, so an unpermitted model fails there regardless of what a static walk returned — but to:

- **reject an unusable submission early**, with a clear message, rather than accepting a run that dies partway through on a model the caller was never allowed to use;
- **record per-model provenance** — Hawk computes a model→group ACL from this set, which gates who may read a run's logs; and
- **apply spec-level guardrails**, such as forbidding a caller-set `api_key`.

Those declarations are spread across the spec:

- a `FlowTask`'s `model` and `model_roles`;
- a `FlowModel`'s `name` and its `default` fallback;
- `defaults.model` and `defaults.model_prefix`;
- the `defaults.task` / `defaults.task_prefix` templates (each a `FlowTask` with its own `model` / `model_roles`);
- `options.scanner.model` and `options.scanner.model_roles` (the scanner runs a model too); and
- every `GenerateConfig.fallback_models` entry — note these are provider-native ids with no `provider/` prefix, so a host cannot compare them against the qualified names it authorizes without normalizing first.

Reproducing that walk outside Flow fails in a specific way. It is not that hosts are careless — it is that a hand-written port is correct against the schema it was written for, and silently becomes incomplete as that schema grows. Hawk's integration carries a private port (`_iter_model_refs` + `_model_ref_to_names` + `_iter_flow_models` in `hawk/core/flow_config.py`): an early version missed `model_roles`, so grader models skipped every check; a later pass found `FlowModel.default` missing too; and `fallback_models` was never walked at all. `options.scanner` is the purest case — added in 0.11.0, after the version Hawk pins, so its port has no way to know the site exists. Nothing on the host's side detects any of this.

A miss is not an authorization bypass, for the reason above; it costs a deferred, harder-to-diagnose failure and a less precise log ACL. Neither justifies treating this as a security boundary, and treating it as one leads to chasing an unbounded set of ways a model can reach the runner (see Scope below).

## The `.default` fallback

`FlowModel.default` is a fully-qualified model name (e.g. `"openai/gpt-4o"`) that Flow passes to `get_model(default=...)`, documented as the fallback used when the named model or role is not found. A single `FlowModel` can therefore *declare* two different models — its `name` and its `default` — so the two are surfaced as distinct references and a host applies identical policy to each.

Note that `default` does not currently take effect: a `FlowModel` with a `default` and no `name` raises `ValueError: Model name is required`, and when `name` is set Inspect resolves `default` only if `model is None`, which Flow never passes (issue #778). It is enumerated anyway, because the field is still in the schema and still user-facing: a spec can set it, so a host enumerating declared model references should see it. Over-counting a declared reference is the safe direction, and an enumeration API should not encode a bug as an omission.

The likely resolution of #778 is to **remove** the field rather than make it work. When that lands, this handling retires with it — drop the `<path>.default` ref, the `"default"` variant of `kind`, and this section. Deliberately not done ahead of time: the field exists today, the snapshot test pins it, and a walk that skipped a live schema field would be under-reporting.

## Design

[_config/model_refs.py](../src/inspect_flow/_config/model_refs.py) exposes `iter_model_refs(spec)` and the `SpecModelRef` result type, both exported from `inspect_flow.api`. The signature and per-field semantics live in the module's docstrings rather than being restated here.

`iter_model_refs` merges defaults first (`apply_defaults` on a copy — pure and idempotent, so an already-loaded spec is unchanged) and then walks the merged spec's declared model fields, yielding one `SpecModelRef` (a new type) per reference in a stable order (tasks, then `options`). Consumers never see `defaults`: they are partial field templates rather than declarations, and every value they carry is reported at the task it actually lands on, with the merged role, `default`, and config. This mirrors the runner, which applies the same merge before instantiating, so the walk cannot disagree with the runner about what a default means. The cost, stated plainly: paths and `ref` objects describe the *merged* spec — a model a caller wrote at `defaults.model` is reported at `tasks[i].model`, and `ref` may be a merged copy rather than the caller's object (`model_copy` is shallow, so an untouched model is still the caller's own — treat refs as read-only either way). A spec whose `includes` are still unexpanded is rejected eagerly with `ValueError` (includes reference other spec files, which cannot be read here; `load_spec` expands and clears them — the check is in a non-generator wrapper so it fires at call time, not first iteration).

`SpecModelRef` is an API-boundary type — returned by one helper and consumed by hosts — not a core Flow type. It never crosses the wire: the host recomputes the enumeration locally at each point that holds the spec (CLI, API, runner).

### `SpecModelRef` is deliberately unhashable

`ref` may be a `FlowModel`, which is mutable. Any hash derived from it goes stale the moment the spec is edited, so a ref inserted into a set becomes unfindable — verified: mutate `FlowModel.name` after insertion and `ref in set` is `False` for the very same object. Pydantic makes `BaseModel` unhashable for exactly this reason, and an earlier revision here defined `__hash__` to work around that `TypeError`, which suppressed a correct signal.

The class is therefore a plain `@dataclass`, **not** `frozen=True`. This is the subtle part: `frozen=True` combined with the default `eq=True` makes dataclasses *generate* a `__hash__` (it is non-frozen `eq=True` that clears it). A revision that merely deleted the explicit `__hash__` while keeping `frozen=True` still produced a hashable type for `str`/`None` refs and an error only for `FlowModel` ones — the data-dependent behavior this decision exists to remove. Dropping `frozen` gives `__hash__ is None` outright and needs no `# type: ignore` (`__hash__ = None` in the body is rejected by pyright as an incompatible override). The cost is that a result's own fields can be reassigned; `ref` was always mutable, so `frozen` only ever gave partial immutability.

Rejected alternatives:

- **Hash `(path, role, kind)` only.** Does not work: the generated `__eq__` still compares `ref`, so lookup fails at equality instead of at hashing. Fixing that needs `ref` excluded from comparison too, which makes two refs over *different* models compare equal — worse semantics for no gain.
- **Keep `__hash__` for `set(iter_model_refs(spec))`.** That was the original justification and it does not hold: paths are unique within a walk, so deduplicating refs is a no-op. The useful operation is `{r.name for r in refs}`, which is what Hawk does and needs no hash.

A `TypeError` at hash time is a loud, correct failure; silent membership failure after mutation is a quiet, wrong one. Reopen this only if a consumer has a concrete need to put refs in a set.

### The `name` property

- `str` ref → the string itself;
- `FlowModel` ref → the name that will actually be used, following the same precedence as `_call_factory`: a string `factory` (or a `FlowFactory` wrapping one) *overrides* `name`, so it is reported instead; a callable `factory` builds the model itself and yields `None` even if `name` is set; otherwise `default_none(ref.name)`;
- `Model` ref → `str(ref)` (its provider-qualified name).

Reporting `name` while a `factory` decides the real model would let a caller declare an allowed model and run another, so `name` tracks construction precedence rather than the `name` field.

Note `FlowModel` is the odd one out here: on every other Flow type a string `factory` is a *registry reference*, but `_create_model` passes it to `get_model(model=...)`, and inspect has no model-factory registry (only `modelapi` providers) — so for a model it is the model id, and anything not shaped `provider/model` raises. A factory-derived name is therefore genuinely enumerable. `from_factory` reports one anyway, so a host with its own no-factories policy can act on it without re-deriving this rule.

A `FlowModel`'s `default` is *not* folded into its `name`; it is emitted as its own `SpecModelRef` at `<path>.default` so a host counts it without special-casing.

## Coverage

One reusable model+roles walker applied to every task at `tasks[i]` (whether a `FlowTask` or an already-instantiated `Task`, whose `model` / `model_roles` resolve to live `Model`s that must still be counted). `defaults.task` / `task_prefix` templates and `defaults.model` / `model_prefix` need no walker of their own: they are merged into the tasks before iteration.

- `model`: `str` / `FlowModel` / live `Model` at `<task>.model`;
- `model_roles[role]`: each entry at `<task>.model_roles[role]`, carrying `role`. A list-valued entry — one role bound to several models (inspect-ai 0.3.261's `ModelRoles` widening; model-graded scorers then grade by majority vote) — yields one ref per element at `<task>.model_roles[role][i]`, each carrying `role`. Reporting the list as a single unenumerable ref would make list-bound roles loadable but unauthorizable under the "reject the unenumerable" composition below.

`role` is the `model_roles` key when present, otherwise the model's own role — `FlowModel.role` is passed to `get_model(role=...)` at *any* model site, and a live `Model` carries the role it was created with — so a role-bound model sitting at `task.model` reports its role rather than `None`. The mapping key wins when both are set, since that is the role the model is registered under for the task; the fallback applies only when the key is *absent*, so even an empty-string key wins. `role` records how a reference is *declared*, not which slot the model ends up serving: a `kind="fallback"` ref is roled only when it comes from a `FlowModel`'s own `config`, which is an argument to the same `get_model` call that binds the role. Fallbacks in a task's `config` are always unroled — that is a task-level generate config where no role participates (`FlowTask.config` explicitly "does not apply to model roles"); the task's role models generate with it too, so pinning it to the default model's role would be wrong.

Spec-level references:

- `options.scanner.model` at `options.scanner.model`;
- `options.scanner.model_roles[role]` at `options.scanner.model_roles[role]`.

`ScannerConfig.model` / `model_roles` are typed `Any`, so only their documented `str | Model` shapes are read, plus `None` at `.model` only — notably *not* a `FlowModel`, which those fields accept structurally but `resolve_models` raises on, so naming it would claim a model that cannot run. Deliberately *not* replicated here: the comma-splitting and list handling in inspect-ai's `resolve_models`, or scout's "use element `[0]`" rule (`resolve_models` strips and returns *all* entries; it is scout that keeps the first). Mirroring another project's runtime normalization means tracking it forever and getting it subtly wrong — an earlier version of this walk split on commas without stripping, reporting `" b/y"` as a model name, and applied `resolve_models`' shapes to `model_roles`, which actually goes through `resolve_model_roles` and does not split comma strings. (`resolve_model_roles` *does* accept list values as of inspect-ai 0.3.261, but scanner role values stay list-rejecting here for a different reason: they are forwarded to scout's `scan()`, which does not accept lists — Flow's scan step guards this with a `PrerequisiteError`. A list at a scanner role therefore remains an unenumerable shape.)

An unrecognized shape yields an unenumerable ref instead. That includes a comma-containing string at `options.scanner.model` — the one field that reaches `resolve_models`, which keeps only the first entry. Reporting the whole string there would be worse than either alternative: it names no model, so a host would gate on a string that cannot run while the model that does run goes unchecked. Neither guess nor pretend. Note this applies to `options.scanner.model` only: `get_model` (task models) and `resolve_model_roles` (role values) do not split, so a comma there is genuinely one name.

**Fail-closed invariant.** A *declared model site* that exists but cannot be read statically yields a `SpecModelRef` rather than nothing — an `Any`-typed model field holding an unrecognized shape, `options.scanner` given as a file path, or a `None` value at a scanner *role* key — `resolve_model_roles` raises on it, so the role is declared but unusable, unlike a `None` at `scanner.model`, which the scan plumbing drops and is genuine absence. Silently dropping it would be indistinguishable from "no model here". The invariant covers primary model sites, not malformed values nested inside a `GenerateConfig` (a non-list `fallback_models` is dropped, since inspect-ai could not execute it either).

**`unenumerable`, not `name is None`, is the signal for "I cannot name this".** `name` is `None` for two unrelated reasons: a model binds but cannot be named (an unreadable site, or a callable `factory`), or the reference declares no model at all — post-merge that means a task-level `FlowModel` with neither `name` nor `factory`, a misconfigured spec that instantiation rejects ("Model name is required") rather than running anything. Only the first is something a host must refuse; `unenumerable` separates the two, and keeps the factory-precedence rule inside this API instead of pushing it back onto every caller. (Before iteration moved to the merged spec, the nameless case was also produced by perfectly ordinary `defaults.model` field templates, which is what made this distinction load-bearing; merging now dissolves those before the walk.)

For every `FlowModel` encountered above with a set `default`, an additional `SpecModelRef` is emitted at `<path>.default` (`ref` is the fallback name string), inheriting the same `role`.

Generation-config fallbacks:

- every `GenerateConfig.fallback_models[i]` entry, at `<config>.fallback_models[i]`, inheriting the owning model's `role`.

`GenerateConfig.fallback_models` names real models that handle requests after a classifier refusal, so — like `FlowModel.default` — each is a distinct model that runs and must be counted. Config is walked wherever it appears post-merge: `FlowTask` and live `Task` `config`, `FlowModel` and live `Model` `config` (at every model site above), and `options.scanner.generate_config`; `defaults.config` merges into each task's config before iteration. Note `apply_defaults` also hoists the default model's own config into the task config, so a fallback declared on `FlowModel.config` is reported at both merged locations — same name, two paths — and a fallback on a *callable-factory* model surfaces only at the task path, which is the one place it genuinely still applies (the model-level config is dead there, but the hoisted task-level copy governs generation).

`GenerateConfig`-typed fields reload from a YAML/JSON wire spec as `GenerateConfig`, but `ScannerConfig.generate_config` is typed `Any` and survives the round-trip as a plain mapping. The walk therefore reads `fallback_models` from either a `GenerateConfig` or a mapping, so a scanner's fallback models are counted on the serialized path (the one a remote host actually submits) as well as in-process.

### How Hawk collapses onto this

- `flow_model_names(spec)` → `{r.name for r in iter_model_refs(spec) if r.name and r.kind != "fallback"}` (the `.default` refs supply the fallback names; `kind == "fallback"` entries are provider-native ids in a different namespace, so they are filtered out rather than authorized as Inspect references);
- `enforce_model_guardrails(spec)` → iterate the refs whose `ref` is a `FlowModel`;
- `options.scanner` models are now covered for free, closing a gap the private port had — for *enumeration*. Not for api-key scrubbing: a scanner model site yields a `str` or `Model`, never a `FlowModel`, so `ScannerConfig.model_args` (the same back door Hawk closes on `FlowModel.model_args`) still needs its own check.
- List-valued task roles relax two invariants a host might have assumed: one path no longer maps to at most one model within a role (elements are indexed under the same `model_roles[role]` prefix), and one role no longer maps to one ref (each element carries the same `role`). Set-of-names collapsing — `{r.name for r in refs}`, what `flow_model_names` computes — is unaffected.

## Scope: what this does and does not guarantee

**Guaranteed: completeness over Flow's own declared schema.** Every field in `FlowSpec` / `FlowTask` / `FlowDefaults` / `FlowModel` (and the model-container candidates `FlowAgent` / `FlowSolver` / `FlowScorer`) that can hold a model reference is walked, and the field-name snapshot test forces every future field on those types through that classification before it can be added. This is the drift problem the API exists to solve: a host copying the walk by hand falls behind Flow's schema. Note the guard forces a *decision*, not correctness — an author can satisfy it by updating the snapshot — and it pins the model-bearing spec types, not every nested Flow type.

**Not guaranteed: that this finds every model a run will actually use.** Anything chosen at run time is invisible to a static walk. Three categories, excluded by construction rather than by omission:

1. **User code** — a callable `factory`, or a hook registered via `@after_instantiate`, can return any model, including one named nowhere in the spec. Unclosable without executing the spec.
2. **Ambient configuration** — a task or scanner with no model resolves `INSPECT_EVAL_MODEL` / `SCOUT_SCAN_MODEL` from the process environment. Note this *is* partly reachable from the spec: `spec.env` is applied to the runner environment by both launchers, so a caller can set those keys there. It is still excluded — the value is an env var consumed by inspect-ai, not a Flow model field, and enumerating it would mean maintaining a list of model-bearing environment variable names.
3. **Free-form constructor args** — inspect-ai's `is_model_dict` materializes any `{"model": ..., "config": ...}` mapping found at any depth inside a registry `args` / `extra_args` mapping into a live `Model`, `model_args.api_key` included. This set is defined by inspect-ai's runtime behavior and changes when inspect-ai changes, not when Flow does.

Note category 3 is about *free-form arg mappings*, not about `Any`-typed fields as such: a Flow-declared field pointing at an inspect-ai type (`options.scanner`, `GenerateConfig`) *is* walked, for that type's documented model shapes. The line is drawn at "declared field with a documented model shape" versus "arbitrary mapping the runner happens to introspect".

Chasing category 3 to completeness is an unbounded commitment against another project's internals, and categories 1 and 2 are not closable at all. So the contract is deliberately drawn at the schema boundary.

**Fail-closed at the edge.** Where a model site exists but cannot be read statically, the walk yields a `SpecModelRef` with `unenumerable` set rather than nothing, so a host policy fires instead of silently seeing an empty set.

**What this means for a host.** Enumeration alone was never sufficient for a policy decision. The sound composition is *reject the unenumerable, then enumerate what remains*: refuse refs where `unenumerable` is `True` (file-path scanners, in-process callable factories; unexpanded `includes` never produce refs — they raise) **and** refs where `from_factory` is `True` — a callable factory serializes to a string factory, so `unenumerable` alone does not catch it on the wire path — plus the things outside this walk entirely — model-bearing constructor args and modelless tasks — a validation concern, sibling to `validate_portable_spec`; then apply policy over `iter_model_refs` across the rest. Given that the gateway is the real authorization point, the value here is failing fast and labelling logs accurately, not gatekeeping.

## Known limitations

An empty result does not prove that no model will generate:

- A task (or scanner) with **no** model resolves the ambient `INSPECT_EVAL_MODEL` / `SCOUT_SCAN_MODEL` at run time (`_runner/instantiate.py` falls back to `resolve_models(NOT_GIVEN)`). Note `_apply_task_defaults` only merges `defaults.model` into an *existing* `task.model`, so a modelless task stays modelless through defaults merging. A host must reject modelless tasks or account for its own host default.
- `args` / `extra_args` mappings are not inspected. This is not only an exotic live-object case: inspect-ai's `is_model_dict` materializes any `{"model": ..., "config": ..., "base_url": ..., "model_args": ...}` mapping found at any depth in a registry args mapping into a live `Model`, and `model_args.api_key` flows through with it. A host that gates on models (or scrubs api keys) must reject or vet those mappings itself.
- User code registered via `@after_instantiate` can replace a task's model after all enumeration — the same arbitrary-code class as a callable factory, but with nothing surfaced at all.

Other limitations:

- `includes` are not descended into — they reference other spec files, which cannot be read here. An unresolved spec is rejected with `ValueError` rather than silently under-reporting; `load_spec` expands and clears the field.
- A scanner supplied as a config-file path (`options.scanner` is a `str`) is not loaded. Unlike `includes`, **no** resolution step ever expands it, so a resolved spec does not help. It yields an `unenumerable` ref rather than nothing.
- A `FlowModel` with a *callable* `factory` yields `name is None` and `unenumerable is True`: a model will bind, but no static name exists. Distinct from a `FlowModel` that merely declares no model (field defaults), which is `name is None` but *not* `unenumerable`.
- `fallback_models` entries are provider-native ids (passed verbatim to the provider), not Inspect `provider/model` references, so a host comparing names across both namespaces must normalize. Branch on `kind == "fallback"` rather than parsing `path` — Hawk needs exactly this distinction today, and without a discriminator it would have to keep a second walk to find them.

A snapshot test on the field names of the Flow spec types (`FlowSpec`, `FlowTask`, `FlowDefaults`, `FlowModel`, `FlowOptions`, and the model-container candidates `FlowAgent` / `FlowSolver` / `FlowScorer`) forces every future field through this classification: adding a field fails the test until the author either extends `iter_model_refs` (a model-bearing field) or updates the snapshot (everything else). `FlowAgent` / `FlowSolver` / `FlowScorer` carry no model field today but are pinned so a future one — e.g. a model-driven agent — cannot escape the walk silently. The scanner's model fields and `GenerateConfig.fallback_models` ride on inspect-ai types (`ScannerConfig`, `GenerateConfig`) and are deliberately outside the snapshot — pinning an external type's fields would be fragile against inspect-ai refactors, the same reason full annotation introspection was rejected.

### Why not derive coverage generically

The sibling `validate_portable_spec` (#785) deliberately does *not* use an allow-list of locations — it walks the real serialization boundary, on the argument that an allow-list fails open. It tried the snapshot approach used here and deleted it. So why not follow?

Because #785 has an **oracle** and this does not. "Can this be serialized?" is answered by running pydantic's own serializer and recording what hits the fallback — a check that already encodes the entire schema, executes, and is free. Re-deriving it by hand would be re-implementing pydantic. There is no comparable oracle for "is this field a model reference", and the two candidates you could synthesise both fail measurably. Measured against a spec producing 15 refs: a walk driven by *field names* finds 12 and invents 1; a walk driven by *type annotations* finds 6. Three concrete falsifiers:

- **`FlowExtraArgs.model`** is a mapping of model-construction kwargs. A name-driven walk reports `extra_args.model['api_key']` as a model reference — a host would run a permission check on a secret and write it into a log ACL.
- **`model_roles` keys are roles; other `dict[str, FlowModel]` fields key differently.** (Historically `defaults.model_prefix` keyed by model-name prefix; merge-first iteration removed it from the walked surface, but the point stands wherever a mapping's key meaning is field-specific.)
- **`Task` and `Model` are not pydantic models**, so a generic child-walk cannot see into them at all — yet a live `Task`'s `model`, `model_roles`, and `config.fallback_models` are real and must be counted.

`role`, `kind`, and the `factory`-over-`name` precedence are likewise properties of *which field a value sits in* and of `_create_model`'s behaviour, present nowhere in the data. A generic walk would recover 40–80% of paths while inventing a false one — strictly worse than a hand walk with a drift guard.

For accuracy about the sibling: #785's walk is not purely value-blind either. It carries its own field-name sets (`_REINFLATED_FIELDS`, `_RESOLVING_FIELDS`) and a separate structural pass for `early_stopping`. The distinction between the two approaches is a gradient, not a dichotomy — the decisive difference is the oracle, not blindness.

**What this costs, honestly.** The snapshot guard covers Flow-owned types only. If inspect-ai adds a model-bearing field to `ScannerConfig` or `GenerateConfig`, this walk silently under-reports and no test fails — whereas #785's technique would catch the analogous change automatically. That is a real advantage of the generic approach, and this repo tracks inspect-ai closely enough (weekly canary, routine reconcile PRs) for the risk to be live rather than theoretical. Pinning an external type's fields was rejected as fragile, so the mitigation is `test_no_model_shaped_value_escapes_unclassified`: it traverses a populated spec generically and asserts every model-shaped value is either walked or explicitly excluded. Discovering by value rather than by field name, it reaches inspect-ai types the snapshot cannot. It is a partial mitigation, not a proof — it cannot see into a live `Task`/`Model` (not pydantic models), and it finds candidates by a `*model*` field-name heuristic, so a field named e.g. `judge` would escape it.
