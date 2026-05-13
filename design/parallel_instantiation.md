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

The current loop in [instantiate.py:116](../src/inspect_flow/_runner/instantiate.py) becomes a dispatch on mode:

```python
def instantiate_tasks(spec: FlowSpec, base_dir: str) -> list[InstantiatedTask]:
    task_configs = spec.tasks or []
    if not task_configs:
        return []
    cfg = resolve_instantiate(spec)
    with RunAction("instantiate") as action:
        progress, progress_task = _make_progress(action, total=len(task_configs))
        if cfg.mode == "serial":
            results = _instantiate_serial(spec, task_configs, base_dir, progress, progress_task, action)
        elif cfg.mode == "by_task":
            results = _instantiate_by_task(spec, task_configs, base_dir, cfg.max_threads, progress, progress_task, action)
        else:  # "parallel"
            results = _instantiate_parallel(spec, task_configs, base_dir, cfg.max_threads, progress, progress_task, action)
        action.update(info=f"Instantiated {len(results)} tasks")
    return results
```

`_instantiate_serial` keeps the existing semantics verbatim. The parallel variants use `concurrent.futures.ThreadPoolExecutor`:

- `_instantiate_parallel` submits every `task_config` and consumes results via `as_completed`.
- `_instantiate_by_task` groups `task_configs` by `get_task_name(task_config)` and submits one future per group; the group worker iterates its configs serially.

Both preserve the **input order** of `task_configs` in the returned list (so downstream behavior — task identifier construction, log-discovery ordering — is unchanged regardless of mode). Implementation: index each input config, fan results back into an ordered list by index.

### Thread-safety considerations

These are real concerns that show up the moment we add threads. Each must be addressed before merging.

1. **`chdir_python(base_dir)` is process-wide and explicitly non-thread-safe** ([inspect_ai/_util/path.py](https://inspect.aisi.org.uk/) `chdir_python` docstring: "Non thread-safe context manager"). It's used inside `_create_task` for local filesystems. All flow tasks share the same `base_dir`, so the fix is to enter `chdir_python(base_dir)` **once** on the main thread around the parallel section, and remove the per-task chdir when running in a parallel mode. `_create_task` accepts a flag (or splits into two helpers) so the inner call skips chdir when already inside an outer one.

2. **`init_active_model` writes a `ContextVar`.** ContextVars are per-context; `ThreadPoolExecutor` copies the submitting context into each worker. Setting it in a worker only affects that worker's view, which is what we want — `_create_task` reads the active model on the same thread.

3. **Inspect AI's registry.** `load_tasks`, `registry_create`, and `scorer_from_spec` read/write module-level registry dicts. Reads are safe; the risky case is two threads loading the *same* Python file at the same time, which can race on import and registry insertion. `by_task` mode avoids this for repeated task names by construction. For `parallel` mode we accept the residual risk and document it — users selecting `parallel` are asserting their factories are safe. If we hit a real-world race we can add a module-level lock around `load_tasks`.

4. **User task factories.** Some factories aren't thread-safe (e.g. shared dataset cache writes, monkey-patches). `by_task` is the escape hatch for users who want parallelism across distinct tasks but not within. We do not attempt to detect non-thread-safe factories.

### Progress and display

`rich.progress.Progress` is thread-safe (uses an internal lock). Worker threads call `progress.update(...)` and `progress.advance(...)` directly. The "current task" description (`description=f"[cyan]{task_name}[/cyan]"`) is less meaningful when multiple tasks are in flight, so in parallel modes we render a count-only description (`"Instantiating ({active} in flight)"`) and drop the per-task name from the progress line. Per-task errors still report which task failed via the error path below.

### Error handling

The current code uses `action.error_context(task_name)` to attach a task name to any exception that bubbles up. With threads, a single shared error context doesn't work.

Strategy: fail fast. As soon as any future raises, cancel pending futures, wait for in-flight workers to return, and re-raise the first failure with its task name prefixed (matching serial behavior).

```python
for fut in as_completed(futures):
    task_name = futures[fut]
    try:
        results_by_index[futures_index[fut]] = fut.result()
    except BaseException as e:
        for other in futures:
            other.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
        raise type(e)(f"{task_name}: {e}") from e
```

In-flight workers can't be interrupted mid-call, so `shutdown(wait=True)` lets them finish before the exception propagates. Already-completed results are discarded — the caller sees the same failure semantics as serial mode.

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
- Thread-safety smoke: a `parallel`-mode test exercising `_create_task` with local filesystem `base_dir` confirms the chdir-once approach works (no `FileNotFoundError` from racing chdirs).
- Error propagation: a flow spec where one task's factory raises confirms the failing task name appears in the surfaced error under all three modes, and that `parallel`/`by_task` modes fail fast (don't wait for unrelated work to complete before raising).

## Open Questions

### 1. Should `by_task` group by `get_task_name` or by something stricter?

`get_task_name` returns the display name. Two `FlowTask` entries with the same `name` field group together. If users set the same `name` for distinct underlying factories, they'd be serialized unexpectedly. Acceptable for v1 — `name` is the user-facing identity of a task and treating it as the grouping key matches user intuition.
