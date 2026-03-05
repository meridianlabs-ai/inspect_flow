# inspect_flow.api


## Python API

### init

Initialize the inspect_flow API.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_api/api.py#L25)

``` python
def init(
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv_base_dir: str | None = ".",
) -> None
```

`log_level` str  
The Inspect Flow log level to use.

`display` [DisplayType](inspect_flow.api.qmd#displaytype)  
The display mode.

`dotenv_base_dir` str \| None  
Directory (or file path) to search for `.env` files. If a file path is
given, its parent directory is used. `None` to skip `.env` loading.
Defaults to `"."` (current working directory).

### run

Run an inspect_flow evaluation.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_api/api.py#L72)

``` python
def run(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    resume: bool = False,
) -> None
```

`spec` [FlowSpec](inspect_flow.qmd#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current
working directory.

`dry_run` bool  
If `True`, do not run eval, but show a count of tasks that would be run.

`resume` bool  
If `True`, reuse the log directory from the previous run.

### load_spec

Load a spec from file.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_api/api.py#L57)

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
A dictionary of arguments to pass as kwargs to the function in the flow
config.

### config

Return the flow spec configuration.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_api/api.py#L106)

``` python
def config(
    spec: FlowSpec,
    base_dir: str | None = None,
) -> str
```

`spec` [FlowSpec](inspect_flow.qmd#flowspec)  
The flow spec configuration.

`base_dir` str \| None  
The base directory for resolving relative paths. Defaults to the current
working directory.

### store_get

Get a FlowStore instance.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_api/api.py#L123)

``` python
def store_get(store: str = "auto", create: bool = True) -> FlowStore
```

`store` str  
The store location. Can be a path to the store directory or `"auto"` for
the default store location.

`create` bool  
Whether to create the store if it does not exist.

### delete_store

Delete a flow store.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_store/store.py#L158)

``` python
def delete_store(store_path: str) -> None
```

`store_path` str  
Path to the store directory.

### copy_all_logs

Copy all log files from src_dir to dest_dir, preserving directory
structure.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_util/logs.py#L16)

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

### FlowStore

Interface for flow store implementations.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_store/store.py#L16)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_store/store.py#L31)

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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_store/store.py#L49)

``` python
@abstractmethod
def get_logs(self) -> set[str]
```

remove_log_prefix  
Remove logs matching the given prefixes.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_store/store.py#L58)

``` python
@abstractmethod
def remove_log_prefix(
    self,
    prefix: str | Sequence[str],
    missing: bool = False,
    recursive: bool = False,
    dry_run: bool = False,
    verbose: bool = True,
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

### DisplayType

Display mode for flow output.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/f32fa5c6540892f2286a893db1b457479185fabf/src/inspect_flow/_display/display.py#L15)

``` python
DisplayType = Literal["full", "rich", "plain"]
```
