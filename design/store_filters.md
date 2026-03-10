### Problem

Users need to control which stored logs are eligible for reuse during `flow run` and when querying the store. The filter should examine `EvalLog` headers (commonly tags, metadata, status, and dates) and act as an additional constraint on top of existing task-identifier matching.

### Filter Type

```python
LogFilter = Callable[[EvalLog], bool]
```

Matches inspect_ai's `list_eval_logs(filter=...)` interface. The filter receives an `EvalLog` loaded in header-only mode (no samples). Returns `True` to include, `False` to exclude.

### Design

#### 1. `FlowStoreConfig` Model

A new Pydantic model that bundles store path with filter configuration:

```python
class FlowStoreConfig(FlowBase):
    """Store configuration with optional log filter."""

    path: Literal["auto"] | str | None = "auto"
    filter: SkipValidation[LogFilter] | str | None = None  # callable, registered name, or None
```

`SkipValidation` is needed because `FlowBase` doesn't allow arbitrary types and Pydantic can't validate callables.

#### 2. `FlowSpec.store` Field (Backwards-Compatible)

The existing `store` field accepts the new type as an additional union member:

```python
class FlowSpec(FlowBase):
    store: Literal["auto"] | str | FlowStoreConfig | None | NotGiven = Field(
        default=not_given
    )
```

Usage:

**Python API — inline lambda:**

```python
spec = FlowSpec(
    store=FlowStoreConfig(
        filter=lambda log: log.status == "success" and "golden" in (log.eval.tags or [])
    ),
    tasks=[...],
)
run(spec)
```

#### 3. Log Filter Registry

A simple module-level registry with a decorator for naming filters.

Usage:

**Python API — registered filter:**

```python
@log_filter
def approved_only(log: EvalLog) -> bool:
    return (
        "approved" in (log.eval.tags or [])
        and log.eval.created >= "2025-01-01"
    )

spec = FlowSpec(
    store=FlowStoreConfig(filter="approved_only"),
    tasks=[...],
)
```

**YAML config (with registered filter defined in `_flow.py`):**

```yaml
store:
  path: ./my-store
  filter: approved_only
```

Registration is optional, users can always pass an inline callable via the Python API.

##### Registry Implementation

The log_filter registry should be implemented using the registry support in inspect_ai.
For now we will not add log_filter to the RegistryType list and will instead ignore type warning for this type.

#### 4. `store_factory` Changes

`store_factory` extracts both path and filter from `FlowStoreConfig`, resolves string filter names via `registry_lookup`, and passes the resolved filter to the `DeltaLakeStore` constructor. Callers (`find_existing_logs`, `run_eval_set`) don't need to know about filters.

#### 5. `FlowStore` Interface Changes

The store holds an internal filter (set at construction) used by `search_for_logs`. `get_logs` accepts an optional per-call filter for public API and CLI use:

```python
class FlowStore(ABC):
    @abstractmethod
    def get_logs(self, filter: LogFilter | None = None) -> set[str]: ...

class FlowStoreInternal(FlowStore):
    @abstractmethod
    def search_for_logs(self, task_ids: set[str]) -> dict[str, str]: ...
```

- `search_for_logs` applies `self._filter` internally.
- `get_logs(filter=...)` applies the per-call filter by reading each log header. This is O(n) file reads vs the current O(1) table scan when no filter is passed.

#### 6. Where the Filter Applies

- **`flow run`**: `store_factory` extracts the filter from `FlowStoreConfig` and stores it in the `DeltaLakeStore`. `search_for_logs` applies `self._filter` to each candidate log after reading its header but **before** the `is_better_log` comparison — filtered-out logs are never considered as candidates.
- **`store.get_logs(filter=...)`**: The per-call filter is applied at query time by reading each log header. Returns only paths whose headers pass the filter.

#### 7. CLI changes

| Command | New Option | Accepts | Notes |
|---|---|---|---|
| `flow run` | `--store-filter` | Registered filter name | Overrides spec's `store.filter` |
| `flow store list` | `--filter` | Registered filter name | Show only matching logs |
| `flow store list` | `--exclude` | Registered filter name | Show only non-matching logs |
| `flow store remove` | `--filter` | Registered filter name | Remove only matching logs |
| `flow store remove` | `--exclude` | Registered filter name | Remove only non-matching logs |

`--filter` and `--exclude` are mutually exclusive. Both accept a registered filter name. `--filter` includes logs that pass; `--exclude` includes logs that fail (inverts the filter).

`--store-filter` cannot use the string override system (`_options_to_overrides`) because setting `store.filter=<name>` would fail when `spec.store` is a plain string like `"auto"`. Instead, follow the `--resume` precedent: add `store_filter: str | None` to `ConfigOptions`, and apply it after spec loading by converting `spec.store` to a `FlowStoreConfig` if needed.

`flow store list` passes the resolved filter (or its negation) to `get_logs(filter=...)`.

`flow store remove` adds a `filter` parameter to `remove_log_prefix`. The implementation already computes a `logs_to_remove: set[str]` from prefix matching; the filter narrows that set by reading each candidate's header and excluding logs that don't pass.
