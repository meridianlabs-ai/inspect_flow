## Problem

Users need a hook that runs **between task instantiation and `eval_set`** — after `instantiate_tasks` has produced concrete `Task` objects, but before they're handed to inspect-ai. Concrete use cases:

- **Reorder / shuffle** the task list (e.g. randomize a sweep, run cheapest tasks first).
- **Filter** tasks (e.g. drop ones whose target log already exists in a sidecar location).
- **Decorate** tasks with computed metadata (e.g. tag with git SHA, compute a per-task budget).
- **Mutate** task properties in batch (e.g. set per-task `time_limit` from external data).

The existing [`@after_load`](../src/inspect_flow/_types/decorator.py) hook is the wrong place: it runs in the **parent process before YAML serialization**, where tasks are still spec-level (`FlowTask`), not instantiated `Task` objects. Anything that needs the resolved `Task` (its dataset, its constructed solver chain, its real `task.name`) has to wait until after `instantiate_tasks` runs — which, for `execution_type="venv"`, happens inside the **child subprocess**.

The goal: `@after_instantiate` works exactly like `@after_load` from the user's perspective — decorate a function anywhere reachable from spec loading or task instantiation, and it runs:

```python
# config.py, _flow.py, an inspect-evals package, a task module, anywhere reachable
from inspect_ai import Task
from inspect_flow import after_instantiate

@after_instantiate
def shuffle(tasks: list[Task]) -> list[Task]:
    import random
    random.shuffle(tasks)
    return tasks
```

In particular, the hook must fire if the decorator lives in:

1. The user's `config.py` (the spec file itself).
2. An auto-included `_flow.py`.
3. A task module loaded from a path (e.g. `./my_task.py@task_name`).
4. A registered Inspect AI plugin / entry-point package installed in the venv (e.g. an `inspect-evals` extension that ships a hook).
5. Anything transitively imported by any of the above.

## How `@after_load` works today, and why it's not enough

The existing pattern (in [_config/load.py](../src/inspect_flow/_config/load.py) and [_util/module_util.py](../src/inspect_flow/_util/module_util.py)):

1. `_load_spec_from_file` executes the config (or `_flow.py`) via `execute_file_and_get_last_result`.
2. It scans the resulting globals for any callable with `INSPECT_FLOW_AFTER_LOAD_ATTR` set, and appends them to `LoadState.after_flow_spec_loaded_funcs`.
3. After `expand_spec` finishes resolving the spec, `_after_flow_spec_loaded(spec, state)` invokes each collected function.

This works for `@after_load` because the relevant scope is "files explicitly loaded by the loader." But `@after_instantiate` has a bigger scope: it needs to discover hooks that come into existence during *task instantiation* (entry points, task module files, transitive imports). Scanning a fixed list of loader-known files misses those.

## Design: registry-based discovery

Use Inspect AI's registry as the discovery channel, mirroring how `@log_filter` works in this codebase already.

### Decorator

```python
# _types/after_instantiate.py
INSPECT_FLOW_AFTER_INSTANTIATE_TYPE = "after_instantiate"

AfterInstantiate: TypeAlias = Callable[[list[Task]], list[Task] | None]

def after_instantiate(func: AfterInstantiate) -> AfterInstantiate:
    """Decorator to register a function to run after tasks are instantiated.

    The decorated function receives `list[Task]` and may return a new list
    (the new tasks) or `None` (leave the list unchanged after in-place edits).
    """
    name = registry_name(func, func.__name__)
    registry_add(
        func,
        RegistryInfo.model_construct(
            type=INSPECT_FLOW_AFTER_INSTANTIATE_TYPE, name=name
        ),
    )
    return func
```

This is structurally identical to `@log_filter` (see [_types/log_filter.py](../src/inspect_flow/_types/log_filter.py)). `model_construct` bypasses Pydantic's literal validation of `RegistryType`, since `"after_instantiate"` is not in inspect_ai's enum.

### Discovery + invocation

In `run_eval_set`, right after `instantiate_tasks` returns:

```python
tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)

hooks = registry_find(
    lambda info: info.type == INSPECT_FLOW_AFTER_INSTANTIATE_TYPE
)
hooks.sort(key=lambda fn: registry_info(fn).name)  # deterministic order

plain_tasks = [t.task for t in tasks]
for hook in hooks:
    with action.error_context(registry_info(hook).name):
        result = hook(plain_tasks)
        if result is not None:
            plain_tasks = result

# eval_set(tasks=plain_tasks, ...)
```

`registry_find` already calls `ensure_entry_points()` if nothing matches, so packaged hooks distributed via entry points are picked up automatically — the same way registered `@scorer` / `@solver` / `@task` are picked up.

**Why the registry is the right primitive here:**

- **Source-agnostic.** Anything that runs the decorator registers a hook. Task module loaded by `load_tasks(path)`? Decorator runs as a side effect of the import — hook registered. Entry-point package activated by `ensure_entry_points()`? Same. Auto-included `_flow.py`? Same.
- **Deduplicated by name.** If a hook ends up imported twice (e.g. a package gets imported as a side effect of two different paths), the registry stores one entry; the hook runs once.
- **Familiar to Inspect users.** Same pattern as every other named-thing in Inspect AI.
- **No per-source plumbing.** We don't have to special-case task files vs entry points vs `_flow.py`; they all funnel through "did the decorator run?"

### Ordering

`registry_find` doesn't guarantee an order. To make hook ordering reproducible regardless of import order, we sort alphabetically by registered name before invoking. Users who care can name their hooks `01_foo`, `02_bar`, etc. — same lever they'd use for log filters.

## The venv bridge: `FlowInternal.python_files`

The registry solves discovery once the decorator has run. There's still a delivery problem for one case: hooks defined in **the user's `config.py` or `_flow.py`**. Those files are executed by the *parent* during spec loading. The parent's registry knows about the hook. The venv child has its own fresh registry and never executes the config file (it reads the resolved `flow.yaml` instead).

For cases 3–5 in the use-case list above (task modules, entry points, transitive imports), the child re-triggers the decorator as a natural side effect of `instantiate_tasks` running. The decorator lands in the child's registry, and the post-instantiation scan finds it. Nothing extra is needed.

For cases 1–2 (config and `_flow.py`), the child has to be told to load these files purely for their decorator side effect. That's the only remaining gap.

### The bridge

Add a `FlowInternal` sub-model on `FlowSpec`. It's *not* a user-facing field — its sole purpose is to ferry loader-known state across the parent→child boundary:

```python
class FlowInternal(FlowBase):
    """State populated by the spec loader. Not intended for direct user configuration."""

    python_files: Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description=(
            "Absolute paths to Python files that the runner should execute "
            "for their side effects (e.g. registering decorators). Loaded "
            "before task instantiation so registrations in these files are "
            "visible in the runner's registry. Populated automatically by "
            "the spec loader from any files that register `@after_instantiate` "
            "(or similar runner-side decorators) at load time."
        ),
    )


class FlowSpec(...):
    ...
    internal: FlowInternal | None | NotGiven = Field(
        default=not_given,
        description=(
            "Internal state populated by the spec loader. Not intended for "
            "direct user configuration."
        ),
    )
```

The field is named generically (`python_files`, not `after_instantiate_files`) because the bridge mechanism is useful for any side-effect-registering decorator that lives in the spec / `_flow.py`, not just `@after_instantiate`. Future runner-side decorators can reuse this exact channel without needing a parallel field.

In the resolved YAML the child reads:

```yaml
internal:
  python_files:
    - /abs/path/_flow.py
    - /abs/path/config.py
```

Why a sub-model instead of a top-level field:

- **Visual segregation.** Anyone opening `flow.yaml` sees `internal:` and knows to leave it alone.
- **Scales.** Future loader-populated state (resolved auto-include manifests, cached resolution data) goes inside `FlowInternal` without growing `FlowSpec`'s top-level surface.
- **Plays nicely with `extra="forbid"`.** Users still get a clean validation error if they typo a real top-level field; only carefully-named keys are allowed inside `internal:`.
- **Discoverable in code.** `spec.internal.python_files` reads as what it is.

### Populating the bridge

In `_load_spec_from_file`, after each file executes, detect whether it registered any `@after_instantiate` hooks during its execution. Two ways to do this:

- **Snapshot-then-diff the registry** around the `exec` call: hooks registered with new names get attributed to this file. Robust but a little fiddly.
- **Scan the file's globals** for callables that registered themselves (set a marker attribute in the decorator, in addition to the registry add): mirrors how `@after_load` discovery already works.

Both work. The second is simpler and matches the existing pattern:

```python
INSPECT_FLOW_AFTER_INSTANTIATE_ATTR = "_inspect_flow_after_instantiate"

def after_instantiate(func: AfterInstantiate) -> AfterInstantiate:
    name = registry_name(func, func.__name__)
    registry_add(func, RegistryInfo.model_construct(
        type=INSPECT_FLOW_AFTER_INSTANTIATE_TYPE, name=name,
    ))
    setattr(func, INSPECT_FLOW_AFTER_INSTANTIATE_ATTR, True)  # for parent discovery
    return func
```

Then in `_load_spec_from_file`:

```python
if any(
    hasattr(v, INSPECT_FLOW_AFTER_INSTANTIATE_ATTR)
    for v in globals.values()
):
    state.python_files.add(config_file)
```

The attribute is purely a convenience for the parent loader's per-file detection. The child does not look at the attribute — it uses the registry.

Then in `expand_spec`, before returning:

```python
if state.python_files:
    internal = (
        spec.internal
        if isinstance(spec.internal, FlowInternal)
        else FlowInternal()
    )
    spec = spec.model_copy(update={
        "internal": internal.model_copy(update={
            "python_files": sorted(state.python_files),
        }),
    })
```

`config_file` is absolutized in `int_load_spec`, so paths in the YAML are absolute — usable from the venv subprocess regardless of its CWD.

### Loading the bridge files in the child

In the child's `run_eval_set`, before the registry scan:

```python
internal = resolved_spec.internal
files = internal.python_files if isinstance(internal, FlowInternal) else None
for file_path in files or []:
    execute_file_and_get_last_result(file_path, args={})  # side effect: decorators register
```

`execute_file_and_get_last_result` already handles `sys.path` setup for local files. We use it purely for the side effect; the returned value is discarded.

After this loop, every hook source has had a chance to register:

- Config + `_flow.py`: loaded just now via the bridge.
- Entry-point packages: will be loaded by `registry_find` → `ensure_entry_points` later.
- Task modules: will be loaded by `instantiate_tasks` later.

Then `instantiate_tasks` runs (more hooks may register as a side effect), then `registry_find` enumerates *all* registered hooks. One discovery mechanism, regardless of where the hook came from.

### Inproc

For `execution_type="inproc"`, parent and child are the same process. Config and `_flow.py` are loaded by the parent's spec-loading, decorators register, and the same `registry_find` scan after `instantiate_tasks` picks them up. The `FlowInternal.python_files` field is populated for consistency (since the spec might still be serialized by `write_config_file`) but is effectively a no-op in inproc — re-loading an already-imported file is idempotent at the registry layer (`registry_add` overwrites with the same callable).

## Why not copy hook files into the venv tempdir?

The user asked about copying Python files into the venv. We considered it and rejected it:

- **Imports break.** A `_flow.py` at the project root commonly does `from my_pkg import helpers`. Copying just `_flow.py` into the tempdir wouldn't bring `my_pkg` with it, and inserting the tempdir at the front of `sys.path` doesn't help — the author's source tree has to be on `sys.path` somewhere either via dependency install or its original on-disk location.
- **Absolute paths already work.** The venv subprocess is on the same machine with full filesystem access; no isolation benefit to copying.
- **No surprises on file moves.** A file path baked into a saved `flow.yaml` is already a path-of-record. Same as for `--filter "file.py@name"` today.

If we ever want a fully-portable `flow.yaml` (movable to another host), that's a separate packaging feature — out of scope here.

## Hook signature

```python
AfterInstantiate: TypeAlias = Callable[[list[Task]], list[Task] | None]
```

A hook receives the full list of `Task` objects. Return a new list, or `None` for "I mutated in place." We deliberately do not expose `InstantiatedTask` (the internal pairing of `flow_task` + `task`) — hooks operating on plain `Task` objects can be tested without constructing a `FlowTask`, and it matches what `eval_set` sees. If a hook needs `FlowTask.flow_metadata`, that information should be propagated onto `Task.metadata` by the instantiation layer; that's a narrower separate change.

Hooks that mutate a `Task` should use `inspect_ai.task_with(task, ...)` rather than assigning to attributes directly. `task_with` is the canonical mutator in Inspect AI (and what `instantiate_tasks` itself uses to apply `FlowTask` overrides), so going through it keeps Flow hooks consistent with the rest of the pipeline and avoids stepping around any normalization Inspect performs on the way in.

## Multiple hooks

All registered `@after_instantiate` hooks run, **serially in alphabetical-by-registered-name order** for reproducibility. Each receives the output of the previous one (or the original list if the previous returned `None`).

There's no parallelism — instantiation is parallel (see [parallel_instantiation.md](parallel_instantiation.md)), but the hook stage is serial.

## Errors

A hook that raises propagates out of `run_eval_set` and surfaces through the existing `RunAction` error path. The display info is set to the hook's registered name so the user can tell which one failed.

## CLI

No new flag. Hooks are decorator-only. The bridge field is populated automatically.

## API

Re-export from `inspect_flow`:

```python
from inspect_flow import after_instantiate
```

No new types or fields in the user-facing API surface — `FlowInternal` is internal-by-name and not re-exported.

## Testing

- **Inproc, hook in config.py**: a config with `@after_instantiate` that reverses the task list — `eval_set` receives tasks reversed.
- **Inproc, hook in `_flow.py`**: same, decorator in an auto-included `_flow.py`.
- **Venv, hook in config.py**: the YAML's `internal.python_files` contains the config path; the child loads it; `eval_set` receives reversed tasks.
- **Venv, hook in `_flow.py`**: same, with `_flow.py` path in the field.
- **Venv, hook in a task module**: a `@after_instantiate` defined in `./my_task.py` (loaded by `load_tasks`) fires in the child *without* its path appearing in `python_files` — confirms registry-based discovery works for task-module sources.
- **Venv, hook from an entry-point package**: a small test package with an `@after_instantiate` registered via entry points is installed into the venv via `additional_dependencies`; the hook fires in the child.
- **Multiple hooks**: two hooks compose in alphabetical-by-name order.
- **Error path**: a hook that raises produces an error whose display info contains the hook's registered name.

## Open Questions

### 1. Should the hook receive `InstantiatedTask` instead of `Task`?

Covered above: no, for v1. Carry `FlowTask.flow_metadata` on `Task.metadata` from the instantiation layer if a hook needs it.

### 2. Interaction with `instantiate=parallel`?

After all instantiation completes — `_instantiate_threaded` returns a fully-ordered list before any hook sees it. No interaction with the parallelism mode.

### 3. Do we want an explicit opt-in field too?

If a future user wants to scope a hook to a specific spec (e.g. one of three decorated functions in `_flow.py` should only run for spec A, not B), we'd need an explicit `after_instantiate: list[str]` field with `"file.py@name"` semantics like `log_filter`. We don't need it for v1 — "all registered hooks fire" matches `@after_load` and is the simplest mental model. Adding it later is non-breaking.

### 4. Should hooks registered by Inspect AI itself (or third-party packages) fire by default?

The registry approach means *any* package whose import path is touched during instantiation can register a hook and have it fire. That's powerful (libraries can ship default behaviors) but also potentially surprising (an `inspect-evals` upgrade adds a hook → user's behavior changes). Mitigations if this becomes a problem: log the list of registered hooks before invoking them; offer an opt-out field on `FlowSpec` to disable specific hooks by name. Out of scope for v1.
