## Problem

`instantiate_tasks` (see [_runner/instantiate.py](../src/inspect_flow/_runner/instantiate.py)) builds every `Task` serially before `eval_set` is called. For large matrix sweeps — hundreds of flow tasks, each with its own model, scorer, and solver factories — this serial phase becomes a noticeable wall-clock cost before any evaluation starts. Common slow steps include loading a task module from disk, building a dataset (e.g. downloading from HuggingFace), and constructing scorers that touch the network.

Task instantiation is synchronous (not async), so the natural parallelism primitive is a thread pool. We want to let users opt into parallel instantiation while keeping the default behavior unchanged.

## Configuration

Add a new field to `FlowSpec`:

```python
class FlowSpec(FlowBase, arbitrary_types_allowed=True):
    ...
    instantiate: (
        Literal["serial", "by_task", "parallel"]
        | InstantiateConfig
        | NotGiven
    ) = Field(
        default=not_given,
        description=(
            "How to instantiate tasks before running. `'serial'` (default) "
            "instantiates one task at a time. `'by_task'` parallelizes across "
            "distinct task names but serializes instances that share a name. "
            "`'parallel'` instantiates everything concurrently. Pass an "
            "`InstantiateConfig` to also set `max_threads`."
        ),
    )
```

Where `InstantiateConfig` is a new model:

```python
class InstantiateConfig(FlowBase):
    """Configuration for task instantiation parallelism."""

    mode: Literal["serial", "by_task", "parallel"] = Field(
        default="serial",
        description="Parallelism mode for `instantiate_tasks`.",
    )
    max_threads: int = Field(
        default=32,
        description="Maximum worker threads to use for instantiation.",
    )
```

### Modes

| Mode | Behavior | When to use |
|---|---|---|
| `serial` (default) | Current behavior: one task at a time. | Safe default; some user factories rely on serial execution (chdir, global imports, network rate limits). |
| `by_task` | Distinct task names instantiate in parallel; instances that share a `task.name` instantiate serially within that group. | Matrix sweeps where each task name has many parameterizations (e.g. many model/temperature variants of the same task). Lets users hand-write a thread-unsafe per-task factory while still parallelizing across different tasks. |
| `parallel` | Every flow task instantiates concurrently up to `max_threads`. | Maximum throughput when factories are known to be thread-safe. |

The string forms (`"serial"`, `"by_task"`, `"parallel"`) are sugar for `InstantiateConfig(mode=...)` with the default `max_threads`. Use the model form to override `max_threads`. This mirrors the `store: Literal["auto"] | str | FlowStoreConfig | None` pattern already in `FlowSpec`.

### Examples

```python
# Strings — pick a mode, accept the default thread cap
spec = FlowSpec(instantiate="by_task", tasks=[...])
spec = FlowSpec(instantiate="parallel", tasks=[...])

# Model — control thread count
spec = FlowSpec(
    instantiate=InstantiateConfig(mode="parallel", max_threads=8),
    tasks=[...],
)
```

```yaml
# YAML — string form
instantiate: by_task

# YAML — model form
instantiate:
  mode: parallel
  max_threads: 8
```

## Implementation

### Normalization

A small helper resolves the union to a single `InstantiateConfig`:

```python
def resolve_instantiate(spec: FlowSpec) -> InstantiateConfig:
    value = spec.instantiate
    if isinstance(value, NotGiven) or value is None:
        return InstantiateConfig()  # mode="serial"
    if isinstance(value, str):
        return InstantiateConfig(mode=value)
    return value
```

### `instantiate_tasks` rewrite

The current loop in [instantiate.py](../src/inspect_flow/_runner/instantiate.py) becomes a dispatch on mode:

```python
def instantiate_tasks(spec: FlowSpec, base_dir: str) -> list[InstantiatedTask]:
    task_configs = list(spec.tasks or [])
    if not task_configs:
        return []
    cfg = _resolve_instantiate(spec)
    with RunAction("instantiate") as action:
        progress = Progress(...)
        action.update(info=progress)
        progress_task = progress.add_task("Instantiating", total=len(task_configs))
        if cfg.mode == "serial":
            results = _instantiate_serial(spec, task_configs, base_dir, action, progress, progress_task)
        else:
            results = _instantiate_threaded(spec, task_configs, base_dir, cfg, action, progress, progress_task)
        action.update(info=f"Instantiated {len(results)} tasks")
    return results
```

`_instantiate_serial` keeps the existing semantics verbatim. `_instantiate_threaded` handles both `parallel` and `by_task` by grouping inputs into **units of work** (a `list[_IndexedSpec]`, where `_IndexedSpec` is a frozen dataclass pairing the input position with its `TaskSpec`):

- In `parallel` mode, each input is its own unit.
- In `by_task` mode, inputs are grouped by `get_task_name(...)` so that all specs sharing a name form one unit and run serially in a single worker.

Units are dispatched to a `concurrent.futures.ThreadPoolExecutor` capped at `min(cfg.max_threads, len(units))`. Each worker returns a `dict[int, list[InstantiatedTask]]` keyed by original position; the main thread merges these as futures complete (no shared-state mutation from workers). Output is sorted by position so the returned list matches input order — downstream behavior (task identifier construction, log-discovery ordering) is unchanged regardless of mode.

### Thread-safety considerations

These are real concerns that show up the moment we add threads. Each must be addressed before merging.

1. **`chdir_python` is process-wide and explicitly non-thread-safe.** It's called by inspect_ai's `load_tasks` (via `load_file_tasks`) and by `scorer_from_spec` whenever the spec resolves to a file path. Both can run on worker threads. We can't simply enter `chdir_python(base_dir)` once on the main thread, because inspect_ai still issues its own nested chdir on each call. Fix: serialize the chdir-using portion with a module-level `_chdir_lock`, used at both `load_tasks` and `scorer_from_spec` call sites. We acquire the lock only when the name is *not* already in its registry — once a task or scorer is registered (via prior file load or `@task` / `@scorer` import), the inspect_ai entry point dispatches straight to `task_create` / `scorer_create` without any chdir, so user code (the `@task` body, which may load datasets) runs unlocked and in parallel. User-visible implication: local file-based specs such as `path/to/task.py@my_task` still serialize on their first load; they only benefit from parallel instantiation after the underlying file has already been imported.

2. **`init_active_model` writes a `ContextVar`.** ContextVars are per-context; `ThreadPoolExecutor` copies the submitting context into each worker. Setting it in a worker only affects that worker's view, which is what we want — `_create_task` reads the active model on the same thread.

3. **`get_model` memoizes into a module-level `_models` dict.** Concurrent writes are atomic under CPython's GIL, so the worst case is two threads constructing the same model and one cached instance being briefly overwritten — no correctness issue. We don't add a lock here.

4. **`registry_create` (used for solvers and agents)** is pure registry lookup — no chdir, no file loading. Safe to call from workers.

5. **User task / scorer / solver / agent factories.** Some factories aren't thread-safe (e.g. shared dataset cache writes, monkey-patches). `by_task` is the escape hatch for users who want parallelism across distinct tasks but not within. We do not attempt to detect non-thread-safe factories.

### Progress and display

`rich.progress.Progress` is thread-safe (uses an internal lock). Worker threads call `progress.advance(...)` directly. The "current task" description (`description=f"[cyan]{task_name}[/cyan]"`) is less meaningful when multiple tasks are in flight, so in threaded modes we set the description to the mode name itself (e.g. `[cyan]parallel[/cyan]`) rather than a single task name. Per-task errors still report which task failed via the error path below.

### Error handling

Strategy: fail fast. As soon as any future raises, cancel pending futures and re-raise the **original** exception unchanged. The task name is surfaced via `action.error_context(...)`, which sets the display info that `RunAction.__exit__` formats when the exception propagates — same mechanism serial mode uses.

```python
for fut in as_completed(futures):
    try:
        results_by_position.update(fut.result())
    except BaseException:
        task_name = futures[fut]
        for other in futures:
            other.cancel()
        with action.error_context(task_name):
            raise
```

We deliberately do **not** wrap with `type(e)(f"{task_name}: {e}")` — that approach breaks for any exception type that doesn't accept a single-string constructor (e.g. `subprocess.CalledProcessError(returncode, cmd)`, or any custom exception with multiple required args), turning the original failure into a `TypeError` from the reconstruction. Callers can pattern-match the original exception type, and the failing task name still appears in the rich display via the action's error context.

In-flight workers can't be interrupted mid-call; `ThreadPoolExecutor.__exit__` waits for them when the `with` block exits, then the exception propagates. Already-completed results are discarded — the caller sees the same failure semantics as serial mode.

## CLI

No new CLI flag in v1 — `instantiate` is a spec field, set via the config file. If demand exists, add `--instantiate <serial|by_task|parallel>` and `--instantiate-threads <N>` later through the standard `_options_to_overrides` mechanism. This keeps the initial surface area small.

## API

`InstantiateConfig` is re-exported from `inspect_flow` so users can construct it in code:

```python
from inspect_flow import FlowSpec, InstantiateConfig, run

run(FlowSpec(
    instantiate=InstantiateConfig(mode="parallel", max_threads=16),
    tasks=[...],
))
```

## Testing

- Unit: `resolve_instantiate` handles every union arm (NotGiven, None, each string, full model).
- Integration: a flow spec with N tasks across M names runs to completion under each mode and produces the same set of `InstantiatedTask` results in the same order.
- Thread-safety smoke: a `parallel`-mode test where the registered task body waits on a `threading.Barrier` confirms multiple workers actually run user task code concurrently (the barrier would time out under serial).
- Error propagation: a flow spec where one task's factory raises confirms the failing task name appears in the surfaced error under all three modes, and that `parallel`/`by_task` modes fail fast (don't wait for unrelated work to complete before raising).

## Open Questions

### 1. Should `by_task` group by `get_task_name` or by something stricter?

`get_task_name` returns the display name. Two `FlowTask` entries with the same `name` field group together. If users set the same `name` for distinct underlying factories, they'd be serialized unexpectedly. Acceptable for v1 — `name` is the user-facing identity of a task and treating it as the grouping key matches user intuition.
