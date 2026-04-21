# inspect_flow.api – Inspect Flow

## Python API

### init

Initialize the inspect_flow API.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/api.py#L27)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/api.py#L74)

``` python
def run(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    resume: bool = False,
) -> None
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current working directory.

`dry_run` bool  
If `True`, do not run eval, but show a count of tasks that would be run.

`resume` bool  
If `True`, reuse the log directory from the previous run.

### check

Check completeness of an inspect_flow evaluation against existing logs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/api.py#L124)

``` python
def check(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    log_dir: str | None = None,
) -> CheckResult | None
```

`spec` [FlowSpec](../reference/inspect_flow.html.md#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current working directory.

`log_dir` str \| None  
Log directory to check against. Overrides the `log_dir` in the spec.

### run_step

Run a step function on the given logs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_steps/run.py#L26)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/api.py#L59)

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

### config

Return the flow spec configuration.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/api.py#L170)

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

### list_logs

List log paths grouped by directory, directories ordered by most recent log file.

Within each directory, logs are sorted by filename timestamp descending. Logs without a timestamp prefix sort at the end.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/list_logs.py#L42)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_api/api.py#L187)

``` python
def store_get(store: str = "auto", create: bool = True) -> FlowStore
```

`store` str  
The store location. Can be a path to the store directory or `"auto"` for the default store location.

`create` bool  
Whether to create the store if it does not exist.

### delete_store

Delete a flow store.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_store/store.py#L205)

``` python
def delete_store(store_path: str) -> None
```

`store_path` str  
Path to the store directory.

### copy_all_logs

Copy all log files from src_dir to dest_dir, preserving directory structure.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_util/logs.py#L91)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_steps/tag.py#L37)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_steps/tag.py#L65)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_steps/copy.py#L21)

``` python
@step
def copy(
    logs: list[EvalLog],
    *,
    dest: str,
    source_prefix: str | None = None,
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

`overwrite` bool  
Overwrite existing files at the destination.

`store` [FlowStore](../reference/inspect_flow.api.html.md#flowstore) \| str \| None  
Optional flow store. The copied log is added to the store.

### FlowStore

Interface for flow store implementations.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_store/store.py#L25)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_store/store.py#L40)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_store/store.py#L58)

``` python
@abstractmethod
def get_logs(self, filter: LogFilter | None = None) -> set[str]
```

`filter` [LogFilter](../reference/inspect_flow.html.md#logfilter) \| None  
Optional filter to apply to log headers. Only logs passing the filter are included. It is an error to specify both a per-call filter and a store-level filter.

remove_log_prefix  
Remove logs matching the given prefixes.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_store/store.py#L72)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_steps/step.py#L24)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/53f086c9b9e0248ce63a652ddb755242aafd9897/src/inspect_flow/_display/display.py#L15)

``` python
DisplayType = Literal["full", "rich", "plain"]
```
