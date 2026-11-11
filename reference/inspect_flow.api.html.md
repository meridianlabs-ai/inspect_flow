# inspect_flow.api – Inspect Flow

## Python API

### init

Initialize the inspect_flow API.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/api.py#L28)

``` python
def init(
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv_base_dir: str | None = ".",
) -> None
```

`log_level` str  
The Inspect Flow log level to use.

`display` [DisplayType](../reference/inspect_flow.api.html.md#displaytype)  
The display mode.

`dotenv_base_dir` str \| None  
Directory (or file path) to search for `.env` files. If a file path is given, its parent directory is used. `None` to skip `.env` loading. Defaults to `"."` (current working directory).

### run

Run an inspect_flow evaluation.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/api.py#L89)

``` python
def run(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    resume: bool = False,
    handle_file: str | None = None,
) -> RunResult
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current working directory.

`dry_run` bool  
If `True`, do not run eval, but show a count of tasks that would be run.

`resume` bool  
If `True`, reuse the log directory from the previous run.

`handle_file` str \| None  
If set, write a JSON launch handle (with the run’s `log_dir` and `pid`) to this file once the log directory is resolved, so an external monitor can discover a backgrounded run. Resolved relative to `base_dir`.

### check

Check completeness of an inspect_flow evaluation against existing logs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/api.py#L176)

``` python
def check(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    log_dir: str | None = None,
) -> CheckResult
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current working directory.

`log_dir` str \| None  
Log directory to check against. Overrides the `log_dir` in the spec.

### run_step

Run a step function on the given logs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_steps/run.py#L27)

``` python
def run_step(
    step: WrappedStepFunction[P],
    logs: list[str] | list[EvalLog] | EvalLog | str,
    dry_run: bool = False,
    filter: LogFilter | str | Sequence[LogFilter | str] | None = None,
    exclude: LogFilter | str | Sequence[LogFilter | str] | None = None,
    recursive: bool = True,
    expand_paths: bool = True,
    store: FlowStore | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> None
```

`step` WrappedStepFunction\[P\]  
The step function to run.

`logs` list\[str\] \| list\[EvalLog\] \| EvalLog \| str  
EvalLog objects or paths to eval logs to process.

`dry_run` bool  
If True, run steps but skip writing logs to disk.

`filter` [LogFilter](../reference/inspect_flow.html.md#logfilter) \| str \| Sequence\[[LogFilter](../reference/inspect_flow.html.md#logfilter) \| str\] \| None  
A log filter or sequence of filters. Only logs that pass all filters are processed. Accepts callables, registered names, or “<file.py@name>” strings.

`exclude` [LogFilter](../reference/inspect_flow.html.md#logfilter) \| str \| Sequence\[[LogFilter](../reference/inspect_flow.html.md#logfilter) \| str\] \| None  
A log filter or sequence of filters. Logs that pass any exclude filter are skipped. Accepts the same formats as filter.

`recursive` bool  
Recurse into directories (default: True).

`expand_paths` bool  
Expand directory paths to individual log paths (default: True). Set to False when paths are already resolved.

`store` [FlowStore](../reference/inspect_flow.api.html.md#flowstore) \| None  
Optional flow store. Written logs are added to the store.

`*args` P.args  
Positional arguments to pass to the step function.

`**kwargs` P.kwargs  
Keyword arguments to pass to the step function.

### load_spec

Load a spec from file.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/api.py#L60)

``` python
def load_spec(
    file: str,
    *,
    args: dict[str, Any] | None = None,
) -> FlowSpec
```

`file` str  
The path to the spec file.

`args` dict\[str, Any\] \| None  
A dictionary of arguments to pass as kwargs to the function in the flow config.

### dump_spec

Dump a flow spec to its canonical wire representation.

The returned dict is JSON-compatible and stable: re-dumping a reloaded spec reproduces it exactly, i.e. `dump_spec(load_spec_data(dump_spec(spec))) == dump_spec(spec)`. Fields that are unset — or explicitly set to their default value — are omitted, so effective values always survive a round trip but `model_fields_set` membership does not. Explicit `None` is preserved, and Flow’s `NotGiven` sentinel never appears. Live values normalize to references (a registered callable to its registry name, a registry object such as a tool in agent args to its reference dict), so a reloaded spec is wire-equivalent to, but not necessarily object-equal to, the original. The runner resolves a name back to a callable only in `factory` fields and `store.filter`; in any other position (e.g. factory `args`) the name reloads as a plain string — `validate_portable_spec` flags these before dumping. Typed values are normalized through validation, so a coercible value assigned without validation (e.g. a numeric string in a float field) dumps in canonical form.

Values in untyped fields (e.g. `flow_metadata`, `model_args`) should be JSON-native; anything else follows pydantic’s JSON coercion (a tuple becomes a list, a `datetime` a string, a set a list in unspecified order) and may not round-trip. In fields that skip validation (e.g. `early_stopping`), serializable live objects carry one-way: they reload as plain data. Arguments captured in a registered object’s params are encoded by inspect-ai at construction time (non-serializable values are already stringified before Flow sees them). Whether a reference resolves in the target process — installed packages, shipped files — is a separate concern; gate portable use with `validate_portable_spec` before dumping. YAML/JSON rendering is left to the caller.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/serialize.py#L19)

``` python
def dump_spec(spec: FlowSpec) -> dict[str, Any]
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec to dump.

### load_spec_data

Reconstruct a flow spec from its canonical wire representation.

Inverse of [dump_spec()](../reference/inspect_flow.api.html.md#dump_spec). Validation is strict: unknown fields are rejected (except in [FlowFactory](../reference/inspect_flow.html.md#flowfactory) mappings, whose API forwards unrecognized keys as factory arguments), as is an embedded `NotGiven` sentinel or a non-finite float (whether present literally or produced by coercing a string such as `"NaN"`). JSON and YAML parsers accept both, but they signal data that did not come from [dump_spec()](../reference/inspect_flow.api.html.md#dump_spec), and a sentinel would be misread as a user value.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/serialize.py#L91)

``` python
def load_spec_data(data: Mapping[str, Any]) -> FlowSpec
```

`data` Mapping\[str, Any\]  
Spec data produced by [dump_spec()](../reference/inspect_flow.api.html.md#dump_spec), possibly after a JSON or YAML round trip.

### config

Return the flow spec configuration.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/api.py#L231)

``` python
def config(
    spec: FlowSpec,
    base_dir: str | None = None,
) -> str
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current working directory.

### validate_portable_spec

Validate that a flow spec can be serialized and recreated in another process.

A portable spec survives the boundary the venv runner and remote orchestrators cross: dumped to YAML/JSON, then re-validated as a [FlowSpec](../reference/inspect_flow.html.md#flowspec) in a fresh process. Values that do not survive it are live (already-instantiated) Inspect objects such as `Task`, `Model`, `Scorer`, `Solver`, and `Agent` — which reload as a `repr` string or a plain dict rather than the object — and callables the child cannot resolve. A serialized callable is looked up in the Inspect registry, so only a registered object (or a registry name string) is portable: an undecorated function is not, even at module level, and neither are lambdas, `functools.partial`, nested functions, classes, and callable objects. Any JSON-serializable data is portable.

Every field is checked, including free-form containers (`args`, `metadata`, `flow_metadata`, scanner params) and any inline [FlowSpec](../reference/inspect_flow.html.md#flowspec) in `includes` — a path string there is not loaded, so an included file’s contents are not checked. The spec is not expanded or resolved, and nothing is installed or launched.

Four limitations. A value Pydantic coerces natively on dump is reported as portable, because it reloads as the coerced type rather than being lost: `tuple` and `set` become `list`, a dataclass or `BaseModel` becomes `dict`, non-string mapping keys become strings, `datetime`/`date`/`UUID`/ `Path`/`Decimal`/`bytes` become strings, and `NaN` becomes `None`. A registered callable is portable only in a field the runner resolves names in — the `factory` fields and `store.filter` — since elsewhere its name reloads as a plain string. And a live registered object in scanner `params` is rejected even though scout would re-inflate it, since that only holds when every scanner entry is a spec reference.

A registered object’s name must also be resolvable in the child. Inspect qualifies names of objects defined in an installed package (`my_pkg/my_task`), which the child can import; a bare name from a loose module relies on that module already being imported and is *not* checked here. Prefer factories from packaged code.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/portable.py#L108)

``` python
def validate_portable_spec(spec: FlowSpec) -> None
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec to validate.

### iter_model_refs

Yield the model references a flow spec will run with.

Defaults are merged before iterating (`apply_defaults` is applied to a copy; it is idempotent, so an already-resolved spec is unchanged). Every ref therefore points at the task or scanner the model actually applies to, with concrete merged values — a model declared in `defaults.model` appears at `tasks[i].model` for each task it lands on, never at a `defaults.*` path. Consumers do not have to reason about defaults, which are partial templates rather than declarations in their own right.

Order is stable: tasks, then `options`. Sites walked: each task’s `model` and `model_roles` (whether a [FlowTask](../reference/inspect_flow.html.md#flowtask) or an already-instantiated `Task`), and `options.scanner`. A list-valued task role (one role bound to several models) yields one ref per element, at an indexed path (`tasks[0].model_roles['grader'][0]`), each carrying the role — so a role may map to several refs. Every `GenerateConfig.fallback_models` entry (on a task, model, or scanner) is yielded at `<config>.fallback_models[i]`, because those models handle requests after a classifier refusal.

Nothing is instantiated, installed, or read from disk — which is why a spec whose `includes` have not been expanded is rejected: includes reference other spec files, and enumerating around them would silently under-report. `load_spec` expands and clears them.

**This will not find every model a run may use.** It reads the model reference fields Flow declares in its own schema; it does not execute anything, so any model chosen at run time is invisible to it:

- **user code** — a callable `factory` or an `@after_instantiate` hook can return any model, including one named nowhere in the spec;
- **ambient configuration** — a task or scanner with no model resolves `INSPECT_EVAL_MODEL` / `SCOUT_SCAN_MODEL` from the environment, which `spec.env` may itself set;
- **free-form constructor args** — most commonly a plain string consumed by user code (`FlowTask(args={"grader_model": "openai/gpt-4o"})`, a `model_graded_qa` scorer’s `model` arg); also any `{"model": ..., "config": ...}` mapping, which inspect-ai materializes into a live model, api key included.

An empty or short result therefore does not prove which models will run. What it does guarantee is that no *declared* spec field is missed as Flow’s schema grows: a snapshot test forces every new field on the model-bearing spec types through this classification.

Where a declared model site exists but cannot be read statically (e.g. a scanner given as a config-file path, or an `Any`-typed field holding an unrecognized shape), a [SpecModelRef](../reference/inspect_flow.api.html.md#specmodelref) is yielded with `unenumerable` set rather than nothing. A host applying policy should reject what it cannot enumerate — refs where `unenumerable` is `True`, and (if it does not permit factories) where `from_factory` is `True`, plus model-bearing constructor args and modelless tasks, which are outside this walk — then apply policy over what this yields.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/model_refs.py#L162)

``` python
def iter_model_refs(spec: FlowSpec) -> Iterator[SpecModelRef]
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec to introspect. Refs report paths and merged values from the defaults-applied spec, not the literal input object.

### list_logs

List log paths grouped by directory, directories ordered by most recent log file.

Within each directory, logs are sorted by filename timestamp descending. Logs without a timestamp prefix sort at the end.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/list_logs.py#L42)

``` python
def list_logs(
    log_dir: str | None = None,
    store: str | FlowStore = "auto",
    since: str | datetime | None = None,
    until: str | datetime | None = None,
) -> list[str]
```

`log_dir` str \| None  
Directory to list logs from recursively. If provided, the store is not used.

`store` str \| [FlowStore](../reference/inspect_flow.api.html.md#flowstore)  
The store to read logs from. Can be a [FlowStore](../reference/inspect_flow.api.html.md#flowstore) instance, a path, or `"auto"` for the default. Only used when `log_dir` is `None`.

`since` str \| datetime \| None  
Only include logs whose filename timestamp is at or after this date. Accepts a `datetime` or a date string. Date strings like `"2024-01-15"` resolve to midnight; relative expressions like `"today"` resolve to the current time.

`until` str \| datetime \| None  
Only include logs whose filename timestamp is at or before this date. Accepts a `datetime` or a date string. Date strings like `"2024-06-01"` resolve to midnight; relative expressions like `"yesterday"` resolve to the current time minus one day.

### store_get

Get a FlowStore instance.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_api/api.py#L248)

``` python
def store_get(store: str = "auto", create: bool = True) -> FlowStore
```

`store` str  
The store location. Can be a path to the store directory or `"auto"` for the default store location.

`create` bool  
Whether to create the store if it does not exist.

### delete_store

Delete a flow store.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_store/store.py#L205)

``` python
def delete_store(store_path: str) -> None
```

`store_path` str  
Path to the store directory.

### copy_all_logs

Copy all log files from src_dir to dest_dir, preserving directory structure.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_util/logs.py#L98)

``` python
def copy_all_logs(src_dir: str, dest_dir: str, dry_run: bool, recursive: bool) -> None
```

`src_dir` str  
Source directory containing log files.

`dest_dir` str  
Destination directory to copy log files to.

`dry_run` bool  
If True, preview what would be copied without making changes.

`recursive` bool  
If True, search src_dir recursively for log files.

### tag

Add or remove tags on eval logs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_steps/tag.py#L37)

``` python
@step
def tag(
    logs: list[EvalLog],
    *,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> list[EvalLog]
```

`logs` list\[EvalLog\]  
EvalLog objects to modify.

`add` list\[str\] \| None  
Tags to add.

`remove` list\[str\] \| None  
Tags to remove.

`author` str \| None  
Provenance author. Defaults to git user.

`reason` str \| None  
Reason for the edit.

### metadata

Set or delete metadata fields on eval logs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_steps/tag.py#L65)

``` python
@step
def metadata(
    logs: list[EvalLog],
    *,
    set: dict[str, Any] | None = None,
    remove: list[str] | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> list[EvalLog]
```

`logs` list\[EvalLog\]  
EvalLog objects to modify.

`set` dict\[str, Any\] \| None  
Key-value pairs to set.

`remove` list\[str\] \| None  
Keys to delete.

`author` str \| None  
Provenance author. Defaults to git user.

`reason` str \| None  
Reason for the edit.

### copy

Copy eval logs to a destination directory.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_steps/copy.py#L39)

``` python
@step
def copy(
    logs: list[EvalLog],
    *,
    dest: str,
    source_prefix: str | None = None,
    suffix: str | None = None,
    rename: Callable[[str], str] | None = None,
    overwrite: bool = False,
    store: FlowStore | str | None = None,  # noqa: ARG001 handled by @step wrapper
) -> list[EvalLog]
```

`logs` list\[EvalLog\]  
list of EvalLog to copy.

`dest` str  
Destination directory (local or S3).

`source_prefix` str \| None  
Directory prefix to strip from source paths. Without this option, files are copied flat into the destination. When provided, preserves directory structure relative to the prefix.

`suffix` str \| None  
Suffix inserted before the file extension of each copy (e.g. `+realigned` copies `probe.eval` to `probe+realigned.eval`). Mutually exclusive with the rename parameter (Python API only).

`rename` Callable\[\[str\], str\] \| None  
Function mapping source filename to destination filename. Python-only. Mutually exclusive with suffix.

`overwrite` bool  
Overwrite existing files at the destination.

`store` [FlowStore](../reference/inspect_flow.api.html.md#flowstore) \| str \| None  
Optional flow store. The copied log is added to the store.

### scan

Run Inspect Scout scanners against the transcripts of eval logs.

Mirrors the CLI surface of `scout scan`, minus `-T/--transcripts` (which flow sources from log paths) and `-F/--filter` (handled by flow’s own `--filter`). Returns scout’s `Status`. For use as a flow step (logs only), see `scan_step`.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_steps/scan.py#L82)

``` python
def scan(
    logs: list[EvalLog],
    scanners: ScannersSpec,
    s: tuple[str, ...] = (),
    scans: str | None = None,
    validation: tuple[str, ...] = (),
    model: str | None = None,
    model_base_url: str | None = None,
    m: tuple[str, ...] = (),
    model_config: str | None = None,
    model_role: tuple[str, ...] = (),
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: int = 0,
    tags: str | None = None,
    metadata: tuple[str, ...] = (),
    cache: int | str | None = None,
    batch: int | str | None = None,
    max_connections: int | None = None,
    max_retries: int | None = None,
    timeout: int | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None,
    reasoning_tokens: int | None = None,
    reasoning_summary: Literal["concise", "detailed", "auto"] | None = None,
    reasoning_history: Literal["none", "all", "last", "auto"] | None = None,
    fail_on_error: bool = False,
    dry_run: bool = False,
) -> Status
```

`logs` list\[EvalLog\]  
EvalLog objects whose transcripts will be scanned.

`scanners` ScannersSpec  
Scanners to run, as a sequence, dict, `ScanJob`, `ScanJobConfig`, or a path to a Python/YAML file containing scanjob/scanner definitions.

`s` tuple\[str, ...\]  
One or more scanjob or scanner arguments (e.g. `-S arg=value`).

`scans` str \| None  
Location to write scan results to.

`validation` tuple\[str, ...\]  
One or more validation set specifications.

`model` str \| None  
Default model for llm scanners.

`model_base_url` str \| None  
Base URL for the model API.

`m` tuple\[str, ...\]  
Native model arguments (e.g. `-M arg=value`).

`model_config` str \| None  
YAML/JSON file with model arguments.

`model_role` tuple\[str, ...\]  
Named model role with model name or YAML/JSON config.

`max_transcripts` int \| None  
Maximum number of transcripts to scan concurrently.

`max_processes` int \| None  
Number of worker processes.

`limit` int \| None  
Limit number of transcripts to scan.

`shuffle` int  
Shuffle order of transcripts (pass a seed for determinism).

`tags` str \| None  
Comma-separated tags for the scan job.

`metadata` tuple\[str, ...\]  
Metadata key=value pairs for the scan job.

`cache` int \| str \| None  
Cache policy for model generations.

`batch` int \| str \| None  
Batch configuration for model requests.

`max_connections` int \| None  
Maximum concurrent connections to the model API.

`max_retries` int \| None  
Maximum retries for model API requests.

`timeout` int \| None  
Model API request timeout in seconds.

`max_tokens` int \| None  
Maximum tokens for completions.

`temperature` float \| None  
Sampling temperature.

`top_p` float \| None  
Nucleus sampling parameter.

`top_k` int \| None  
Top-k sampling parameter.

`reasoning_effort` Literal\['minimal', 'low', 'medium', 'high'\] \| None  
Reasoning effort level (OpenAI o-series, gpt-5).

`reasoning_tokens` int \| None  
Maximum reasoning tokens (Anthropic Claude).

`reasoning_summary` Literal\['concise', 'detailed', 'auto'\] \| None  
Reasoning summary style (OpenAI).

`reasoning_history` Literal\['none', 'all', 'last', 'auto'\] \| None  
Reasoning history inclusion style.

`fail_on_error` bool  
Re-raise scanner exceptions instead of capturing them.

`dry_run` bool  
Print resolved scanners and transcript counts without scanning.

### FlowStore

Interface for flow store implementations.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_store/store.py#L25)

``` python
class FlowStore(ABC)
```

#### Attributes

`store_path` str  
The path to the store directory.

`version` str  
The store version.

#### Methods

import_log_path  
Import a log file(s) or directory(ies) into the store.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_store/store.py#L40)

``` python
@abstractmethod
def import_log_path(
    self,
    log_path: str | Sequence[str],
    recursive: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> None
```

`log_path` str \| Sequence\[str\]  
Path or paths to log files or directories containing log files.

`recursive` bool  
Whether to search directories recursively.

`dry_run` bool  
Preview what would be imported without making changes

`verbose` bool  
Print paths of files being added

get_logs  
Get all log file paths in the store.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_store/store.py#L58)

``` python
@abstractmethod
def get_logs(self, filter: LogFilter | None = None) -> set[str]
```

`filter` [LogFilter](../reference/inspect_flow.html.md#logfilter) \| None  
Optional filter to apply to log headers. Only logs passing the filter are included. It is an error to specify both a per-call filter and a store-level filter.

remove_log_prefix  
Remove logs matching the given prefixes.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_store/store.py#L72)

``` python
@abstractmethod
def remove_log_prefix(
    self,
    prefix: str | Sequence[str],
    missing: bool = False,
    recursive: bool = False,
    dry_run: bool = False,
    verbose: bool = True,
    filter: LogFilter | None = None,
) -> None
```

`prefix` str \| Sequence\[str\]  
One or more prefixes to match against log paths.

`missing` bool  
Whether to remove log paths that are missing from the file system.

`recursive` bool  
Whether to remove log files recursively.

`dry_run` bool  
Preview what would be removed without making changes

`verbose` bool  
Print paths of files being removed

`filter` [LogFilter](../reference/inspect_flow.html.md#logfilter) \| None  
Optional filter to narrow which matched logs are removed. Each candidate log’s header is read and only those passing the filter are removed.

### StepResult

Fine-grained return type for @step functions.

Steps can also return a sequence of EvalLog directly (equivalent to StepResult(logs=logs, modified=True)) or \[\] (equivalent to StepResult(modified=False, skip_log_steps=True)).

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_steps/step.py#L40)

``` python
class StepResult(NamedTuple)
```

#### Attributes

`logs` list\[EvalLog\]  
The logs returned to the caller.

`modified` bool  
Whether the logs were modified. When True, the logs are written back to disk and becomes the current log for subsequent nested steps. When False, the log is returned but the current context log is not advanced.

`flush` bool  
Write all dirty logs immediately, even if nested inside an outer step.

`skip_log_steps` bool  
Skip remaining steps for this log. run_step will move to the next log.

### DisplayType

Display type for flow output.

Matches Inspect’s set of display types: - “full”: Full interactive display with progress bars and rich formatting. - “conversation”: Stream the model conversation to the terminal. - “rich”: Rich text formatting without interactive elements. - “plain”: Plain text output. - “log”: Flat, ANSI-free log lines. - “none”: No display output.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_display/display.py#L16)

``` python
DisplayType = Literal["full", "conversation", "rich", "plain", "log", "none"]
```

### SpecModelRef

A single model reference found in a flow spec.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/model_refs.py#L28)

``` python
@dataclass
class SpecModelRef
```

#### Attributes

`path` str  
Field path of the reference (e.g. `"tasks[0].model_roles['grader']"`).

`ref` str \| [FlowModel](../reference/inspect_flow.html.md#flowmodel) \| Model \| None  
The reference as it appears in the spec: a model name string, a [FlowModel](../reference/inspect_flow.html.md#flowmodel), or an already-instantiated `Model`. `None` marks a model site that exists but cannot be read statically (e.g. a scanner given as a config-file path).

`role` str \| None  
The named role this reference is bound to, or `None` for an unroled model.

Taken from the `model_roles` key, falling back to `FlowModel.role` (which is passed to `get_model(role=...)` at any model site); the mapping key wins when both are set.

This records how the reference is *declared*, not which slot the model will end up serving. So a `kind="fallback"` ref is roled only when it comes from a [FlowModel](../reference/inspect_flow.html.md#flowmodel)’s own `config` — that config is an argument to the same `get_model` call that binds the role. A fallback in a `FlowTask.config` is always `None`: that is a task-level generate config (its field description says it “does not apply to model roles”), so no role participates at that layer — the task’s `model_roles` models generate with it too.

`kind` Literal\['model', 'fallback'\]  
Which kind of reference this is, and hence which namespace `name` is in.

`"model"` is an Inspect `provider/model` reference. `"fallback"` is a `GenerateConfig.fallback_models` entry, which is a provider-native id with no provider prefix. A host comparing or authorizing names across both must branch on this rather than parse `path`.

`name` str \| None  
The model name that will actually be used, or `None` if not static.

A [FlowModel](../reference/inspect_flow.html.md#flowmodel)’s string `factory` takes precedence over `name`, so it is reported instead — unlike other Flow types, that string is not a factory registry reference but the model id itself, passed to `get_model(model=...)` (see `from_factory`). A callable `factory` builds the model itself and yields `None` even when `name` is set. A live `Model` reports its provider-qualified name.

`None` has two causes, distinguished by `unenumerable`: either a model binds here but its name cannot be known statically, or the reference declares no model at all (a [FlowModel](../reference/inspect_flow.html.md#flowmodel) with neither `name` nor `factory` — after defaults merging that is a misconfigured task, which instantiation rejects). Key policy on `unenumerable` rather than on this — and note `unenumerable` is not by itself sufficient: a *string* `factory` is enumerable but its name is a factory id, so a host feeding `name` to a model lookup should check `from_factory` too.

Names are Inspect `provider/model` references, except entries from `GenerateConfig.fallback_models`, which are provider-native ids passed verbatim to the provider (e.g. `"claude-opus-4-5"`).

A model reached through a `base_url` override still reports its Inspect id, which is an assertion about identity rather than a guarantee of which endpoint serves the request.

`from_factory` bool  
Whether `name` came from `FlowModel.factory` rather than `name`.

For a [FlowModel](../reference/inspect_flow.html.md#flowmodel) a string `factory` *is* the model id — it is passed to `get_model(model=...)`, and inspect has no separate model-factory registry — so such a ref is still enumerable. But `factory` means “registry name” on every other Flow type, and a host may have its own policy against factories; this reports one without making the caller unwrap [FlowFactory](../reference/inspect_flow.html.md#flowfactory) and re-derive the precedence rule.

`unenumerable` bool  
Whether a model binds here whose name is not statically knowable.

`True` for a model site this walk cannot read (`ref is None`) and for a [FlowModel](../reference/inspect_flow.html.md#flowmodel) built by a callable `factory`. `False` when `name` is `None` merely because the reference declares no model — a [FlowModel](../reference/inspect_flow.html.md#flowmodel) with neither `name` nor `factory`, which instantiation rejects rather than running anything.

This is the signal for “I cannot name the model”, and a host that cannot allow what it cannot name should reject specs where this is `True`, without rejecting ordinary field-default templates. It is not the only thing a host may want to reject: see `from_factory` for names that are known but derived from `FlowModel.factory`.

Note a callable factory is only `True` in-process: serializing a spec rewrites it to a `file.py@attr` string, which reloads as a string factory and is reported as a name (the name `_call_factory` will then resolve). Such a name is not a `provider/model` reference, so it fails an allow-list rather than passing one.

### SpecNotPortableError

Raised when a flow spec cannot be serialized and recreated in another process.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/portable.py#L72)

``` python
class SpecNotPortableError(ValueError)
```

#### Methods

\_\_init\_\_  
Create the error.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/portable.py#L80)

``` python
def __init__(
    self, violations: list[SpecViolation], hint: str | None = None
) -> None
```

`violations` list\[[SpecViolation](../reference/inspect_flow.api.html.md#specviolation)\]  
Every violation found, each with its field path.

`hint` str \| None  
Extra guidance appended to the rendered message, for a caller with an escape hatch the validator should not assume.

### SpecViolation

A single reason a flow spec is not portable.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/b4899117766084f0d465d464493a652fd9b622bc/src/inspect_flow/_config/portable.py#L59)

``` python
@dataclass
class SpecViolation
```
