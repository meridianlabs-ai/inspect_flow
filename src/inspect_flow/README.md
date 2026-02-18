# Inspect Flow Internals

## _types Module

[_types](./_types) defines the types used in inspect flow configurations.

[flow_config.py](./_types/flow_config.py) defines the pydantic types for the configuration. These types have a "Flow" prefix, e.g. `FlowTask`.

[type_gen.py](./_types/type_gen.py) defines the code generation logic that generates TypedDict classes based on the pydantic types.
These generated types are in [generated.py](./_types/generated.py).

`FlowTaskDict` and other types with a `Dict` suffix are TypedDicts corresponding to the Pydantic types.
These are used primarily to unpack kwargs in the _with functions.
`FlowTaskMatrixDict` and the other types with a `MatrixDict` suffix are TypedDicts that store lists instead of single values.
These are for use in the matrix functions with lists for their field types.

[factories.py](./_types/factories.py) defines three types of functions.
The `_with` functions apply fields to all objects in a list. For example `task_with` sets fields on a list of tasks (specified as a list of string, `FTask`, `FlowTask`, and `FlowTaskDict`).
The `_matrix` functions, like `tasks_matrix` generate lists of types from the product of lists of field values.

## _api Module

[_api](./_api) defines the public API for inspect flow.
This includes the main entry points for running flows and interacting with the framework.
These functions correspond to the CLI commands defined in the [_cli](./_cli) module.

Key functions in [api.py](./_api/api.py):
- `init()` initializes logging, display, and dotenv for the session.
- `run()` launches a flow from a spec.
- `config()` returns the YAML config string for a spec.
- `store_get()` returns a `FlowStore` instance for managing stored logs.

## _cli Module

[_cli](./_cli) defines the command line interface for inspect flow.

Commands:
- `flow run` runs a flow from a configuration file. Defined in [run.py](./_cli/run.py).
- `flow config` outputs the resolved configuration. Defined in [config.py](./_cli/config.py).
- `flow store` manages the log store. Defined in [store.py](./_cli/store.py). Subcommands: `import`, `remove`, `list`, `info`, `delete`.

[options.py](./_cli/options.py) defines shared CLI option decorators (`output_options`, `config_options`) and helpers for parsing them.

## _config Module

[_config](./_config) is responsible for loading and validating the flow configuration. The main function is `load_config`, defined in [config.py](./_config/config.py).

## _launcher Module

[_launcher](./_launcher) is responsible for creating the virtual environment, installing package dependencies, and starting the flow runner process.
The main function is `launch`, defined in [launch.py](./_launcher/launch.py).

## _runner Module

[_runner](./_runner) is responsible for running the flow tasks either in-process or within the virtual environment.

The main function is `run_eval_set`, defined in [run.py](./_runner/run.py). This orchestrates:
1. Resolving the flow configuration into a canonical representation with all defaults set.
2. Instantiating the tasks and dependencies (converting config into inspect AI objects).
3. Finding existing logs in the log directory and store to avoid re-running completed evaluations.
4. Running the remaining tasks via `eval_set`.
5. Adding completed logs to the store.

Other key files:
- [cli.py](./_runner/cli.py) defines the Click entry point for the venv subprocess.
- [logs.py](./_runner/logs.py) handles log discovery and matching — finding existing logs by task identifier from both the log directory and the store.
- [task_log.py](./_runner/task_log.py) formats the task/log summary table shown before evaluation.
- [instantiate.py](./_runner/instantiate.py) converts flow config types into inspect AI eval objects.
- [resolve.py](./_runner/resolve.py) applies defaults and resolves the python version.

## _store Module

[_store](./_store) provides a persistent store for tracking evaluation logs across runs.
The store indexes logs by task identifier so the runner can find and reuse completed evaluations.

[store.py](./_store/store.py) defines the abstract `FlowStore` interface (public) and `FlowStoreInternal` (used by the runner).
`store_factory()` resolves the store path — `"auto"` uses a platform-specific default location, `None` disables the store, or an explicit path can be provided.

[deltalake.py](./_store/deltalake.py) implements the store using Delta Lake (PyArrow + deltalake), supporting both local filesystems and S3.

## _display Module

[_display](./_display) provides a pluggable terminal display for rendering flow progress and status.

[display.py](./_display/display.py) defines the `Display` ABC and manages a global singleton.
`DisplayType = Literal["full", "rich", "plain"]` controls the display mode.
`create_display()` creates a display context with action tracking for CLI commands.

Display implementations:
- [full_actions.py](./_display/full_actions.py) — `FullActionsDisplay`: Rich Live bordered table with action spinners, scrollable messages, progress bars, and captured stdout/stderr.
- [full.py](./_display/full.py) — `FullDisplay`: Simpler Rich display with action status icons.
- [plain.py](./_display/plain.py) — `PlainDisplay`: ASCII-only output.

[run_action.py](./_display/run_action.py) defines `RunAction`, a context manager that tracks a named step (running/success/error). This is the primary integration point used by the runner.

[path_progress.py](./_display/path_progress.py) provides progress display helpers for file scanning operations.

## _util Module

[_util](./_util) defines utility functions and classes used throughout the inspect flow codebase.

- [console.py](./_util/console.py) — Rich console utilities: `flow_print()` for formatted output, `path()` for file path display, and text formatting helpers.
- [error.py](./_util/error.py) — Exception handling: `set_exception_hook()` installs clean error display without tracebacks for handled errors.
- [logging.py](./_util/logging.py) — `init_flow_logging()` and `PrefixLogger` for prefixed log messages.
- [logs.py](./_util/logs.py) — `copy_all_logs()` for copying log files between directories.
- [path_util.py](./_util/path_util.py) — Path helpers: `absolute_path_relative_to()`, `cwd_relative_path()`.
- [subprocess_util.py](./_util/subprocess_util.py) — `signal_ready_and_wait()` for parent-child process synchronization, `run_with_logging()` for subprocess execution.
- [not_given.py](./_util/not_given.py) — Helpers for `NotGiven` sentinel handling.
