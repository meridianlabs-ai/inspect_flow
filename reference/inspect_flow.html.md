# inspect_flow


## Types

### FlowAgent

Configuration for an Agent.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L180)

``` python
class FlowAgent(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the agent. Used to create the agent if the factory is not
provided.

`factory` [FlowFactory](inspect_flow.qmd#flowfactory)\[Agent\] \| Callable\[..., Agent\] \| str \| None \| NotGiven  
Factory function to create the agent instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to agent constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the agent.

`type` Literal\['agent'\] \| None  
Type needed to differentiated solvers and agents in solver lists.

### FlowDefaults

Default field values for Inspect objects. Will be overriden by more
specific settings.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L659)

``` python
class FlowDefaults(FlowBase)
```

#### Attributes

`config` GenerateConfig \| None \| NotGiven  
Default model generation options. Will be overriden by settings on the
`FlowModel` and `FlowTask`.

`agent` [FlowAgent](inspect_flow.qmd#flowagent) \| None \| NotGiven  
Field defaults for agents.

`agent_prefix` dict\[str, [FlowAgent](inspect_flow.qmd#flowagent)\] \| None \| NotGiven  
Agent defaults for agent name prefixes. E.g. `{'inspect/': FAgent(...)}`

`model` [FlowModel](inspect_flow.qmd#flowmodel) \| None \| NotGiven  
Field defaults for models.

`model_prefix` dict\[str, [FlowModel](inspect_flow.qmd#flowmodel)\] \| None \| NotGiven  
Model defaults for model name prefixes. E.g. `{'openai/': FModel(...)}`

`solver` [FlowSolver](inspect_flow.qmd#flowsolver) \| None \| NotGiven  
Field defaults for solvers.

`solver_prefix` dict\[str, [FlowSolver](inspect_flow.qmd#flowsolver)\] \| None \| NotGiven  
Solver defaults for solver name prefixes. E.g.
`{'inspect/': FSolver(...)}`

`task` [FlowTask](inspect_flow.qmd#flowtask) \| None \| NotGiven  
Field defaults for tasks.

`task_prefix` dict\[str, [FlowTask](inspect_flow.qmd#flowtask)\] \| None \| NotGiven  
Task defaults for task name prefixes. E.g.
`{'inspect_evals/': FTask(...)}`

### FlowDependencies

Configuration for flow dependencies to install in the venv.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L704)

``` python
class FlowDependencies(FlowBase)
```

#### Attributes

`dependency_file` Literal\['auto', 'no_file'\] \| str \| None \| NotGiven  
Path to a dependency file (either `requirements.txt` or
`pyproject.toml`) to use to create the virtual environment. If `'auto'`,
will search the path starting from the same directory as the config file
(when using the CLI) or `base_dir` arg (when using the API) looking for
`pyproject.toml` or `requirements.txt` files. If `'no_file'`, no
dependency file will be used. Defaults to `'auto'`.

`additional_dependencies` str \| Sequence\[str\] \| None \| NotGiven  
Dependencies to pip install. E.g. PyPI package specifiers or Git
repository URLs.

`auto_detect_dependencies` bool \| None \| NotGiven  
If `True`, automatically detect and install dependencies from names of
objects in the config (defaults to `True`). For example, if a model name
starts with `'openai/'`, the `'openai'` package will be installed. If a
task name is `'inspect_evals/mmlu'` then the `'inspect-evals'` package
will be installed.

`uv_sync_args` str \| Sequence\[str\] \| None \| NotGiven  
Additional arguments to pass to `uv sync` when creating the virtual
environment using a `pyproject.toml` file. May be a string
(`'--dev --extra test'`) or a list of strings
(`['--dev', '--extra', 'test']`).

### FlowEpochs

Configuration for task epochs.

Number of epochs to repeat samples over and optionally one or more
reducers used to combine scores from samples across epochs. If not
specified the “mean” score reducer is used.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L214)

``` python
class FlowEpochs(FlowBase)
```

#### Attributes

`epochs` int  
Number of epochs.

`reducer` str \| Sequence\[str\] \| None \| NotGiven  
One or more reducers used to combine scores from samples across epochs
(defaults to `"mean"`)

### FlowFactory

Type-checked factory wrapper for creating Inspect AI objects.

Wraps a factory callable with its arguments, binding them at
construction time so that type errors are caught immediately rather than
at evaluation time. Works with `FlowTask`, `FlowAgent`, `FlowSolver`,
`FlowScorer`, and `FlowModel`.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L255)

``` python
class FlowFactory(BaseModel, Generic[R], arbitrary_types_allowed=True)
```

### FlowModel

Configuration for a Model.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L75)

``` python
class FlowModel(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the model to use. If factory is not provided, this is used to
create the model.

`factory` [FlowFactory](inspect_flow.qmd#flowfactory)\[Model\] \| Callable\[..., Model\] \| str \| None \| NotGiven  
Factory function to create the model instance.

`role` str \| None \| NotGiven  
Optional named role for model (e.g. for roles specified at the task or
eval level). Provide a default as a fallback in the case where the role
hasn’t been externally specified.

`default` str \| None \| NotGiven  
Optional. Fallback model in case the specified model or role is not
found. Should be a fully qualified model name (e.g. `openai/gpt-4o`).

`config` GenerateConfig \| None \| NotGiven  
Configuration for model. Config values will be override settings on the
`FlowTask` and `FlowSpec`.

`base_url` str \| None \| NotGiven  
Optional. Alternate base URL for model.

`api_key` str \| None \| NotGiven  
Optional. API key for model.

`memoize` bool \| None \| NotGiven  
Use/store a cached version of the model based on the parameters to
`get_model()`. Defaults to `True`.

`model_args` CreateArgs \| None \| NotGiven  
Additional args to pass to model constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the model.

### FlowOptions

Evaluation options.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L464)

``` python
class FlowOptions(FlowBase)
```

#### Attributes

`retry_attempts` int \| None \| NotGiven  
Maximum number of retry attempts before giving up (defaults to 10).

`retry_wait` float \| None \| NotGiven  
Time to wait between attempts, increased exponentially (defaults to 30,
resulting in waits of 30, 60, 120, 240, etc.). Wait time per-retry will
in no case be longer than 1 hour.

`retry_connections` float \| None \| NotGiven  
Reduce `max_connections` at this rate with each retry (defaults to 1.0,
which results in no reduction).

`retry_cleanup` bool \| None \| NotGiven  
Cleanup failed log files after retries (defaults to `True`).

`sandbox` SandboxEnvironmentType \| None \| NotGiven  
Sandbox environment type (or optionally a str or tuple with a shorthand
spec).

`sandbox_cleanup` bool \| None \| NotGiven  
Cleanup sandbox environments after task completes (defaults to `True`).

`tags` Sequence\[str\] \| None \| NotGiven  
Tags to associate with this evaluation run.

`metadata` dict\[str, Any\] \| None \| NotGiven  
Metadata to associate with this evaluation run.

`trace` bool \| None \| NotGiven  
Trace message interactions with evaluated model to terminal.

`display` [DisplayType](inspect_flow.api.qmd#displaytype) \| None \| NotGiven  
Task display type (defaults to `'rich'`).

`approval` str \| ApprovalPolicyConfig \| None \| NotGiven  
Tool use approval policies. Either a path to an approval policy config
file or a list of approval policies. Defaults to no approval policy.

`score` bool \| None \| NotGiven  
Score output (defaults to `True`).

`log_level` str \| None \| NotGiven  
Level for logging to the console: `"debug"`, `"http"`, `"sandbox"`,
`"info"`, `"warning"`, `"error"`, `"critical"`, or `"notset"` (defaults
to `"warning"`).

`log_level_transcript` str \| None \| NotGiven  
Level for logging to the log file (defaults to `"info"`).

`log_format` Literal\['eval', 'json'\] \| None \| NotGiven  
Format for writing log files (defaults to `"eval"`, the native
high-performance format).

`limit` int \| None \| NotGiven  
Limit evaluated samples (defaults to all samples).

`sample_shuffle` bool \| int \| None \| NotGiven  
Shuffle order of samples (pass a seed to make the order deterministic).

`fail_on_error` bool \| float \| None \| NotGiven  
`True` to fail on first sample error(default); `False` to never fail on
sample errors; Value between 0 and 1 to fail if a proportion of total
samples fails. Value greater than 1 to fail eval if a count of samples
fails.

`continue_on_fail` bool \| None \| NotGiven  
`True` to continue running and only fail at the end if the
`fail_on_error` condition is met. `False` to fail eval immediately when
the `fail_on_error` condition is met (default).

`retry_on_error` int \| None \| NotGiven  
Number of times to retry samples if they encounter errors (defaults to
3).

`debug_errors` bool \| None \| NotGiven  
Raise task errors (rather than logging them) so they can be debugged
(defaults to `False`).

`model_cost_config` str \| dict\[str, ModelCost\] \| None \| NotGiven  
YAML or JSON file with model prices for cost tracking.

`max_samples` int \| None \| NotGiven  
Maximum number of samples to run in parallel (default is
`max_connections`).

`max_tasks` int \| None \| NotGiven  
Maximum number of tasks to run in parallel (defaults is 10).

`max_subprocesses` int \| None \| NotGiven  
Maximum number of subprocesses to run in parallel (default is
`os.cpu_count()`).

`max_sandboxes` int \| None \| NotGiven  
Maximum number of sandboxes (per-provider) to run in parallel.

`log_samples` bool \| None \| NotGiven  
Log detailed samples and scores (defaults to `True`).

`log_realtime` bool \| None \| NotGiven  
Log events in realtime (enables live viewing of samples in inspect view)
(defaults to `True`).

`log_images` bool \| None \| NotGiven  
Log base64 encoded version of images, even if specified as a filename or
URL (defaults to `False`).

`log_model_api` bool \| None \| NotGiven  
Log raw model api requests and responses. Note that error
requests/responses are always logged.

`log_refusals` bool \| None \| NotGiven  
Log warnings for model refusals.

`log_buffer` int \| None \| NotGiven  
Number of samples to buffer before writing log file. If not specified,
an appropriate default for the format and filesystem is chosen (10 for
most all cases, 100 for JSON logs on remote filesystems).

`log_shared` bool \| int \| None \| NotGiven  
Sync sample events to log directory so that users on other systems can
see log updates in realtime (defaults to no syncing). Specify `True` to
sync every 10 seconds, otherwise an integer to sync every `n` seconds.

`bundle_dir` str \| None \| NotGiven  
If specified, the log viewer and logs generated by this eval set will be
bundled into this directory. Relative paths will be resolved relative to
the config file (when using the CLI) or `base_dir` arg (when using the
API).

`bundle_overwrite` bool \| None \| NotGiven  
Whether to overwrite files in the `bundle_dir` (defaults to `False`).

`log_dir_allow_dirty` bool \| None \| NotGiven  
If `True`, allow the log directory to contain unrelated logs. If
`False`, ensure that the log directory only contains logs for tasks in
this eval set (defaults to `False`).

`eval_set_id` str \| None \| NotGiven  
ID for the eval set. If not specified, a unique ID will be generated.

`embed_viewer` bool \| None \| NotGiven  
If True, embed a log viewer into the log directory.

`bundle_url_mappings` dict\[str, str\] \| None \| NotGiven  
Replacements applied to `bundle_dir` to generate a URL. If provided and
`bundle_dir` is set, the mapped URL will be written to stdout.

### FlowScorer

Configuration for a Scorer.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L128)

``` python
class FlowScorer(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the scorer. Used to create the scorer if the factory is not
provided.

`factory` [FlowFactory](inspect_flow.qmd#flowfactory)\[Scorer\] \| Callable\[..., Scorer\] \| str \| None \| NotGiven  
Factory function to create the scorer instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to scorer constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the scorer.

### FlowSolver

Configuration for a Solver.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L154)

``` python
class FlowSolver(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the solver. Used to create the solver if the factory is not
provided.

`factory` [FlowFactory](inspect_flow.qmd#flowfactory)\[Solver\] \| Callable\[..., Solver\] \| str \| None \| NotGiven  
Factory function to create the solver instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to solver constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the solver.

### FlowSpec

Top-level flow specification.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L757)

``` python
class FlowSpec(FlowBase, arbitrary_types_allowed=True)
```

#### Attributes

`includes` Sequence\[str \| [FlowSpec](inspect_flow.qmd#flowspec)\] \| None \| NotGiven  
List of other flow specs to include. Relative paths will be resolved
relative to the config file (when using the CLI) or `base_dir` arg (when
using the API). In addition to this list of explicit files to include,
any `_flow.py` files in the same directory or any parent directory of
the config file (when using the CLI) or `base_dir` arg (when using the
API) will also be included automatically.

`store` Literal\['auto'\] \| str \| [FlowStoreConfig](inspect_flow.qmd#flowstoreconfig) \| None \| NotGiven  
Path to directory to use for flow storage, or a `FlowStoreConfig` with
path and filter options. `'auto'` will use a default application
location. `None` will disable storage. Relative paths will be resolved
relative to the config file (when using the CLI) or `base_dir` arg (when
using the API). If not given, `'auto'` will be used.

`log_dir` str \| None \| NotGiven  
Output path for logging results (required to ensure that a unique
storage scope is assigned). Must be set before running the flow spec.
Relative paths will be resolved relative to the config file (when using
the CLI) or `base_dir` arg (when using the API).

`log_dir_create_unique` bool \| None \| NotGiven  
If `True`, create a unique log directory by appending a datetime
subdirectory (e.g. `2025-12-09T17-36-43`) under the specified `log_dir`.
If `False`, use the existing `log_dir` (which must be empty or have
`log_dir_allow_dirty=True`). Defaults to `False`.

`execution_type` Literal\['inproc', 'venv'\] \| None \| NotGiven  
Execution environment for running tasks (defaults to `'inproc'`).

`python_version` str \| None \| NotGiven  
Python version to use in the flow virtual environment (e.g. `'3.11'`).

`dependencies` [FlowDependencies](inspect_flow.qmd#flowdependencies) \| None \| NotGiven  
Dependencies to install in the venv. Defaults to auto-detecting
dependencies from `pyproject.toml`, `requirements.txt`, and object names
in the config.

`options` [FlowOptions](inspect_flow.qmd#flowoptions) \| None \| NotGiven  
Arguments for calls to `eval_set()`.

`env` dict\[str, str\] \| None \| NotGiven  
Environment variables to set when running tasks.

`defaults` [FlowDefaults](inspect_flow.qmd#flowdefaults) \| None \| NotGiven  
Defaults values for Inspect objects.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the model.

`tasks` Sequence\[str \| [FlowTask](inspect_flow.qmd#flowtask) \| Task\] \| None \| NotGiven  
Tasks to run

### FlowStoreConfig

Store configuration with optional log filter.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L728)

``` python
class FlowStoreConfig(FlowBase)
```

#### Attributes

`path` Literal\['auto'\] \| str \| None  
Path to directory to use for flow storage. `'auto'` will use a default
application location. `None` will disable storage.

`filter` SkipValidation\[[LogFilter](inspect_flow.qmd#logfilter)\] \| str \| Sequence\[SkipValidation\[[LogFilter](inspect_flow.qmd#logfilter)\] \| str\] \| None  
Log filter to apply when searching for existing logs. Can be a callable,
a registered filter name, a sequence of filters (all must pass), or
`None`.

`read` bool  
Whether to match existing logs from the store. Default is `False`.

`write` bool  
Whether to index completed logs in the store. Default is `True`.

### FlowTask

Configuration for an evaluation task.

Tasks are the basis for defining and running evaluations.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L308)

``` python
class FlowTask(FlowBase, arbitrary_types_allowed=True)
```

#### Attributes

`name` str \| None \| NotGiven  
Task name. Any of registry name (`"inspect_evals/mbpp"`), file name
(`"./my_task.py"`), or a file name and attr
(`"./my_task.py@task_name"`). Used to create the task if the factory is
not provided.

`factory` [FlowFactory](inspect_flow.qmd#flowfactory)\[Task\] \| Callable\[..., Task\] \| str \| None \| NotGiven  
Factory function to create the task instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to task constructor

`extra_args` FlowExtraArgs \| None \| NotGiven  
Extra args to provide to creation of inspect objects for this task. Will
override args provided in the `args` field on the `FlowModel`,
`FlowSolver`, `FlowScorer`, and `FlowAgent`.

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| [FlowAgent](inspect_flow.qmd#flowagent) \| Solver \| Agent \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Solver\] \| None \| NotGiven  
Solver or list of solvers. Defaults to `generate()`, a normal call to
the model.

`scorer` str \| [FlowScorer](inspect_flow.qmd#flowscorer) \| Scorer \| Sequence\[str \| [FlowScorer](inspect_flow.qmd#flowscorer) \| Scorer\] \| None \| NotGiven  
Scorer or list of scorers used to evaluate model output.

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Model \| None \| NotGiven  
Default model for task (Optional, defaults to eval model).

`config` GenerateConfig \| NotGiven  
Model generation config for default model (does not apply to model
roles). Will override config settings on the `FlowSpec`. Will be
overridden by settings on the `FlowModel`.

`model_roles` ModelRolesConfig \| None \| NotGiven  
Named roles for use in `get_model()`.

`sandbox` SandboxEnvironmentType \| None \| NotGiven  
Sandbox environment type (or optionally a str or tuple with a shorthand
spec)

`approval` str \| ApprovalPolicyConfig \| None \| NotGiven  
Tool use approval policies. Either a path to an approval policy config
file or an approval policy config. Defaults to no approval policy.

`epochs` int \| [FlowEpochs](inspect_flow.qmd#flowepochs) \| None \| NotGiven  
Epochs to repeat samples for and optional score reducer function(s) used
to combine sample scores (defaults to `"mean"`)

`fail_on_error` bool \| float \| None \| NotGiven  
`True` to fail on first sample error (default); `False` to never fail on
sample errors; Value between 0 and 1 to fail if a proportion of total
samples fails. Value greater than 1 to fail eval if a count of samples
fails.

`continue_on_fail` bool \| None \| NotGiven  
`True` to continue running and only fail at the end if the
`fail_on_error` condition is met. `False` to fail eval immediately when
the `fail_on_error` condition is met (default).

`message_limit` int \| None \| NotGiven  
Limit on total messages used for each sample.

`token_limit` int \| None \| NotGiven  
Limit on total tokens used for each sample.

`time_limit` int \| None \| NotGiven  
Limit on clock time (in seconds) for samples.

`working_limit` int \| None \| NotGiven  
Limit on working time (in seconds) for sample. Working time includes
model generation, tool calls, etc. but does not include time spent
waiting on retries or shared resources.

`cost_limit` float \| None \| NotGiven  
Limit on total cost (in dollars) for each sample. Requires model cost
data via model_cost_config.

`early_stopping` SkipValidation\[EarlyStopping\] \| None \| NotGiven  
Early stopping callbacks.

`version` int \| str \| NotGiven  
Version of task (to distinguish evolutions of the task spec or breaking
changes to it)

`tags` Sequence\[str\] \| None \| NotGiven  
Tags to associate with the task.

`metadata` dict\[str, Any\] \| None \| NotGiven  
Additional metadata to associate with the task.

`sample_id` str \| int \| Sequence\[str \| int\] \| None \| NotGiven  
Evaluate specific sample(s) from the dataset.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the task.

`model_name` str \| None \| NotGiven  
Get the model name from the model field.

Returns: The model name if set, otherwise None.

## Type Aliases

### LogFilter

A function that receives an `EvalLog` (header-only) and returns `True`
to include the log or `False` to exclude it.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/flow_types.py#L38)

``` python
LogFilter: TypeAlias = Callable[[EvalLog], bool]
```

## Decorators

### after_load

Decorator to mark a function to be called after a FlowSpec is loaded.

The decorated function should have the signature (args are all optional
and may be omitted):

``` python
def after_flow_spec_loaded(
    spec: FlowSpec,
    files: list[str],
) -> None:
    ...
```

- `spec`: The loaded `FlowSpec`.
- `files`: List of file paths that were loaded to create the `FlowSpec`.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/decorator.py#L9)

``` python
def after_load(func: F) -> F
```

`func` F  
The function to decorate.

### log_filter

Decorator to register a log filter function.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/log_filter.py#L20)

``` python
def log_filter(func: Callable[[EvalLog], bool]) -> Callable[[EvalLog], bool]
```

`func` Callable\[\[EvalLog\], bool\]  
A function that takes an EvalLog and returns True to include.

## Functions

### agents_matrix

Create a list of agents from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L245)

``` python
def agents_matrix(
    *,
    agent: str | FlowAgent | Sequence[str | FlowAgent],
    args: Sequence[Mapping[str, Any] | NotGiven | None] | None = ...,
) -> list[FlowAgent]
```

`agent` str \| [FlowAgent](inspect_flow.qmd#flowagent) \| Sequence\[str \| [FlowAgent](inspect_flow.qmd#flowagent)\]  
The agent or list of agents to matrix.

`args` Sequence\[Mapping\[str, Any\] \| NotGiven \| None\] \| None  
Additional args to pass to agent constructor.

### agents_with

Set fields on a list of agents.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L175)

``` python
def agents_with(
    *,
    agent: str | FlowAgent | Sequence[str | FlowAgent],
    name: str | NotGiven | None = ...,
    factory: str | NotGiven | None = ...,
    args: Mapping[str, Any] | NotGiven | None = ...,
    flow_metadata: Mapping[str, Any] | NotGiven | None = ...,
    type: Literal['agent'] | None = ...,
) -> list[FlowAgent]
```

`agent` str \| [FlowAgent](inspect_flow.qmd#flowagent) \| Sequence\[str \| [FlowAgent](inspect_flow.qmd#flowagent)\]  
The agent or list of agents to set fields on.

`name` str \| NotGiven \| None  
Name of the agent. Used to create the agent if the factory is not
provided.

`factory` str \| NotGiven \| None  
Factory function to create the agent instance.

`args` Mapping\[str, Any\] \| NotGiven \| None  
Additional args to pass to agent constructor.

`flow_metadata` Mapping\[str, Any\] \| NotGiven \| None  
Optional. Metadata stored in the flow config. Not passed to the agent.

`type` Literal\['agent'\] \| None  
Type needed to differentiated solvers and agents in solver lists.

### configs_matrix

Create a list of generate configs from the product of lists of field
values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L259)

``` python
def configs_matrix(
    *,
    config: GenerateConfig | Sequence[GenerateConfig] | None = ...,
    system_message: Sequence[str | None] | None = ...,
    max_tokens: Sequence[int | None] | None = ...,
    top_p: Sequence[float | None] | None = ...,
    temperature: Sequence[float | None] | None = ...,
    stop_seqs: Sequence[Sequence[str] | None] | None = ...,
    best_of: Sequence[int | None] | None = ...,
    frequency_penalty: Sequence[float | None] | None = ...,
    presence_penalty: Sequence[float | None] | None = ...,
    logit_bias: Sequence[Mapping[str, float] | None] | None = ...,
    seed: Sequence[int | None] | None = ...,
    top_k: Sequence[int | None] | None = ...,
    num_choices: Sequence[int | None] | None = ...,
    logprobs: Sequence[bool | None] | None = ...,
    top_logprobs: Sequence[int | None] | None = ...,
    parallel_tool_calls: Sequence[bool | None] | None = ...,
    internal_tools: Sequence[bool | None] | None = ...,
    max_tool_output: Sequence[int | None] | None = ...,
    cache_prompt: Sequence[Literal['auto'] | bool | None] | None = ...,
    reasoning_effort: Sequence[Literal['none', 'minimal', 'low', 'medium', 'high', 'xhigh'] | None] | None = ...,
    reasoning_tokens: Sequence[int | None] | None = ...,
    reasoning_summary: Sequence[Literal['none', 'concise', 'detailed', 'auto'] | None] | None = ...,
    reasoning_history: Sequence[Literal['none', 'all', 'last', 'auto'] | None] | None = ...,
    response_schema: Sequence[ResponseSchema | None] | None = ...,
    extra_body: Sequence[Mapping[str, Any] | None] | None = ...,
) -> list[GenerateConfig]
```

`config` GenerateConfig \| Sequence\[GenerateConfig\] \| None  
The config or list of configs to matrix.

`system_message` Sequence\[str \| None\] \| None  
Override the default system message.

`max_tokens` Sequence\[int \| None\] \| None  
The maximum number of tokens that can be generated in the completion
(default is model specific).

`top_p` Sequence\[float \| None\] \| None  
An alternative to sampling with temperature, called nucleus sampling,
where the model considers the results of the tokens with top_p
probability mass.

`temperature` Sequence\[float \| None\] \| None  
What sampling temperature to use, between 0 and 2. Higher values like
0.8 will make the output more random, while lower values like 0.2 will
make it more focused and deterministic.

`stop_seqs` Sequence\[Sequence\[str\] \| None\] \| None  
Sequences where the API will stop generating further tokens. The
returned text will not contain the stop sequence.

`best_of` Sequence\[int \| None\] \| None  
Generates best_of completions server-side and returns the ‘best’ (the
one with the highest log probability per token). vLLM only.

`frequency_penalty` Sequence\[float \| None\] \| None  
Number between -2.0 and 2.0. Positive values penalize new tokens based
on their existing frequency in the text so far, decreasing the model’s
likelihood to repeat the same line verbatim. OpenAI, Google, Grok, Groq,
vLLM, and SGLang only.

`presence_penalty` Sequence\[float \| None\] \| None  
Number between -2.0 and 2.0. Positive values penalize new tokens based
on whether they appear in the text so far, increasing the model’s
likelihood to talk about new topics. OpenAI, Google, Grok, Groq, vLLM,
and SGLang only.

`logit_bias` Sequence\[Mapping\[str, float\] \| None\] \| None  
Map token Ids to an associated bias value from -100 to 100
(e.g. “42=10,43=-10”). OpenAI, Grok, Grok, and vLLM only.

`seed` Sequence\[int \| None\] \| None  
Random seed. OpenAI, Google, Mistral, Groq, HuggingFace, and vLLM only.

`top_k` Sequence\[int \| None\] \| None  
Randomly sample the next word from the top_k most likely next words.
Anthropic, Google, HuggingFace, vLLM, and SGLang only.

`num_choices` Sequence\[int \| None\] \| None  
How many chat completion choices to generate for each input message.
OpenAI, Grok, Google, TogetherAI, vLLM, and SGLang only.

`logprobs` Sequence\[bool \| None\] \| None  
Return log probabilities of the output tokens. OpenAI, Grok, TogetherAI,
Huggingface, llama-cpp-python, vLLM, and SGLang only.

`top_logprobs` Sequence\[int \| None\] \| None  
Number of most likely tokens (0-20) to return at each token position,
each with an associated log probability. OpenAI, Grok, Huggingface,
vLLM, and SGLang only.

`parallel_tool_calls` Sequence\[bool \| None\] \| None  
Whether to enable parallel function calling during tool use (defaults to
True). OpenAI and Groq only.

`internal_tools` Sequence\[bool \| None\] \| None  
Whether to automatically map tools to model internal implementations
(e.g. ‘computer’ for anthropic).

`max_tool_output` Sequence\[int \| None\] \| None  
Maximum tool output (in bytes). Defaults to 16 \* 1024.

`cache_prompt` Sequence\[Literal\['auto'\] \| bool \| None\] \| None  
Whether to cache the prompt prefix. Defaults to “auto”, which will
enable caching for requests with tools. Anthropic only.

`reasoning_effort` Sequence\[Literal\['none', 'minimal', 'low', 'medium', 'high', 'xhigh'\] \| None\] \| None  
Constrains effort on reasoning. Defaults vary by provider and model and
not all models support all values (please consult provider documentation
for details).

`reasoning_tokens` Sequence\[int \| None\] \| None  
Maximum number of tokens to use for reasoning. Anthropic Claude models
only.

`reasoning_summary` Sequence\[Literal\['none', 'concise', 'detailed', 'auto'\] \| None\] \| None  
Provide summary of reasoning steps (OpenAI reasoning models only). Use
‘auto’ to access the most detailed summarizer available for the current
model (defaults to ‘auto’ if your organization is verified by OpenAI).

`reasoning_history` Sequence\[Literal\['none', 'all', 'last', 'auto'\] \| None\] \| None  
Include reasoning in chat message history sent to generate.

`response_schema` Sequence\[ResponseSchema \| None\] \| None  
Request a response format as JSONSchema (output should still be
validated). OpenAI, Google, Mistral, vLLM, and SGLang only.

`extra_body` Sequence\[Mapping\[str, Any\] \| None\] \| None  
Extra body to be sent with requests to OpenAI compatible servers.
OpenAI, vLLM, and SGLang only.

### configs_with

Set fields on a list of generate configs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L189)

``` python
def configs_with(
    *,
    config: GenerateConfig | Sequence[GenerateConfig],
    max_retries: int | None = ...,
    timeout: int | None = ...,
    attempt_timeout: int | None = ...,
    max_connections: int | None = ...,
    system_message: str | None = ...,
    max_tokens: int | None = ...,
    top_p: float | None = ...,
    temperature: float | None = ...,
    stop_seqs: Sequence[str] | None = ...,
    best_of: int | None = ...,
    frequency_penalty: float | None = ...,
    presence_penalty: float | None = ...,
    logit_bias: Mapping[str, float] | None = ...,
    seed: int | None = ...,
    top_k: int | None = ...,
    num_choices: int | None = ...,
    logprobs: bool | None = ...,
    top_logprobs: int | None = ...,
    parallel_tool_calls: bool | None = ...,
    internal_tools: bool | None = ...,
    max_tool_output: int | None = ...,
    cache_prompt: Literal['auto'] | bool | None = ...,
    verbosity: Literal['low', 'medium', 'high'] | None = ...,
    effort: Literal['low', 'medium', 'high', 'max'] | None = ...,
    reasoning_effort: Literal['none', 'minimal', 'low', 'medium', 'high', 'xhigh'] | None = ...,
    reasoning_tokens: int | None = ...,
    reasoning_summary: Literal['none', 'concise', 'detailed', 'auto'] | None = ...,
    reasoning_history: Literal['none', 'all', 'last', 'auto'] | None = ...,
    response_schema: ResponseSchema | None = ...,
    extra_headers: Mapping[str, str] | None = ...,
    extra_body: Mapping[str, Any] | None = ...,
    modalities: Sequence[Literal['image'] | ImageOutput] | None = ...,
    cache: bool | CachePolicy | None = ...,
    batch: bool | int | BatchConfig | None = ...,
) -> list[GenerateConfig]
```

`config` GenerateConfig \| Sequence\[GenerateConfig\]  
The config or list of configs to set fields on.

`max_retries` int \| None  
Maximum number of times to retry request (defaults to unlimited).

`timeout` int \| None  
Timeout (in seconds) for an entire request (including retries).

`attempt_timeout` int \| None  
Timeout (in seconds) for any given attempt (if exceeded, will abandon
attempt and retry according to max_retries).

`max_connections` int \| None  
Maximum number of concurrent connections to Model API (default is model
specific).

`system_message` str \| None  
Override the default system message.

`max_tokens` int \| None  
The maximum number of tokens that can be generated in the completion
(default is model specific).

`top_p` float \| None  
An alternative to sampling with temperature, called nucleus sampling,
where the model considers the results of the tokens with top_p
probability mass.

`temperature` float \| None  
What sampling temperature to use, between 0 and 2. Higher values like
0.8 will make the output more random, while lower values like 0.2 will
make it more focused and deterministic.

`stop_seqs` Sequence\[str\] \| None  
Sequences where the API will stop generating further tokens. The
returned text will not contain the stop sequence.

`best_of` int \| None  
Generates best_of completions server-side and returns the ‘best’ (the
one with the highest log probability per token). vLLM only.

`frequency_penalty` float \| None  
Number between -2.0 and 2.0. Positive values penalize new tokens based
on their existing frequency in the text so far, decreasing the model’s
likelihood to repeat the same line verbatim. OpenAI, Google, Grok, Groq,
vLLM, and SGLang only.

`presence_penalty` float \| None  
Number between -2.0 and 2.0. Positive values penalize new tokens based
on whether they appear in the text so far, increasing the model’s
likelihood to talk about new topics. OpenAI, Google, Grok, Groq, vLLM,
and SGLang only.

`logit_bias` Mapping\[str, float\] \| None  
Map token Ids to an associated bias value from -100 to 100
(e.g. “42=10,43=-10”). OpenAI, Grok, Grok, and vLLM only.

`seed` int \| None  
Random seed. OpenAI, Google, Mistral, Groq, HuggingFace, and vLLM only.

`top_k` int \| None  
Randomly sample the next word from the top_k most likely next words.
Anthropic, Google, HuggingFace, vLLM, and SGLang only.

`num_choices` int \| None  
How many chat completion choices to generate for each input message.
OpenAI, Grok, Google, TogetherAI, vLLM, and SGLang only.

`logprobs` bool \| None  
Return log probabilities of the output tokens. OpenAI, Grok, TogetherAI,
Huggingface, llama-cpp-python, vLLM, and SGLang only.

`top_logprobs` int \| None  
Number of most likely tokens (0-20) to return at each token position,
each with an associated log probability. OpenAI, Grok, Huggingface,
vLLM, and SGLang only.

`parallel_tool_calls` bool \| None  
Whether to enable parallel function calling during tool use (defaults to
True). OpenAI and Groq only.

`internal_tools` bool \| None  
Whether to automatically map tools to model internal implementations
(e.g. ‘computer’ for anthropic).

`max_tool_output` int \| None  
Maximum tool output (in bytes). Defaults to 16 \* 1024.

`cache_prompt` Literal\['auto'\] \| bool \| None  
Whether to cache the prompt prefix. Defaults to “auto”, which will
enable caching for requests with tools. Anthropic only.

`verbosity` Literal\['low', 'medium', 'high'\] \| None  
Constrains the verbosity of the model’s response. Lower values will
result in more concise responses, while higher values will result in
more verbose responses. GPT 5.x models only (defaults to “medium” for
OpenAI models).

`effort` Literal\['low', 'medium', 'high', 'max'\] \| None  
Control how many tokens are used for a response, trading off between
response thoroughness and token efficiency. Anthropic Claude Opus 4.5
and 4.6 only (`max` only supported on 4.6).

`reasoning_effort` Literal\['none', 'minimal', 'low', 'medium', 'high', 'xhigh'\] \| None  
Constrains effort on reasoning. Defaults vary by provider and model and
not all models support all values (please consult provider documentation
for details).

`reasoning_tokens` int \| None  
Maximum number of tokens to use for reasoning. Anthropic Claude models
only.

`reasoning_summary` Literal\['none', 'concise', 'detailed', 'auto'\] \| None  
Provide summary of reasoning steps (OpenAI reasoning models only). Use
‘auto’ to access the most detailed summarizer available for the current
model (defaults to ‘auto’ if your organization is verified by OpenAI).

`reasoning_history` Literal\['none', 'all', 'last', 'auto'\] \| None  
Include reasoning in chat message history sent to generate.

`response_schema` ResponseSchema \| None  
Request a response format as JSONSchema (output should still be
validated). OpenAI, Google, Mistral, vLLM, and SGLang only.

`extra_headers` Mapping\[str, str\] \| None  
Extra headers to be sent with requests. Not supported for AzureAI,
Bedrock, and Grok.

`extra_body` Mapping\[str, Any\] \| None  
Extra body to be sent with requests to OpenAI compatible servers.
OpenAI, vLLM, and SGLang only.

`modalities` Sequence\[Literal\['image'\] \| ImageOutput\] \| None  
Additional output modalities to enable beyond text (e.g. \[“image”\]).
OpenAI and Google only.

`cache` bool \| CachePolicy \| None  
Policy for caching of model generate output.

`batch` bool \| int \| BatchConfig \| None  
Use batching API when available. True to enable batching with default
configuration, False to disable batching, a number to enable batching of
the specified batch size, or a BatchConfig object specifying the
batching configuration.

### merge

Merge two flow objects, with `add` values overriding `base` values.

Only explicitly set fields in `add` override `base` — unset fields
(defaulting to `NotGiven`) are ignored. Nested fields like `config` and
`flow_metadata` are merged recursively rather than replaced.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/merge.py#L52)

``` python
def merge(base: _T, add: _T) -> _T
```

`base` \_T  
The base object providing default values.

`add` \_T  
The object to merge into the base. Only explicitly set fields override
those in `base`.

### models_matrix

Create a list of models from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L274)

``` python
def models_matrix(
    *,
    model: str | FlowModel | Sequence[str | FlowModel],
    config: Sequence[GenerateConfig | NotGiven | None] | None = ...,
) -> list[FlowModel]
```

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Sequence\[str \| [FlowModel](inspect_flow.qmd#flowmodel)\]  
The model or list of models to matrix.

`config` Sequence\[GenerateConfig \| NotGiven \| None\] \| None  
Configuration for model. Config values will be override settings on the
`FlowTask` and `FlowSpec`.

### models_with

Set fields on a list of models.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L203)

``` python
def models_with(
    *,
    model: str | FlowModel | Sequence[str | FlowModel],
    name: str | NotGiven | None = ...,
    factory: str | NotGiven | None = ...,
    role: str | NotGiven | None = ...,
    default: str | NotGiven | None = ...,
    config: GenerateConfig | NotGiven | None = ...,
    base_url: str | NotGiven | None = ...,
    api_key: str | NotGiven | None = ...,
    memoize: bool | NotGiven | None = ...,
    model_args: Mapping[str, Any] | NotGiven | None = ...,
    flow_metadata: Mapping[str, Any] | NotGiven | None = ...,
) -> list[FlowModel]
```

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Sequence\[str \| [FlowModel](inspect_flow.qmd#flowmodel)\]  
The model or list of models to set fields on.

`name` str \| NotGiven \| None  
Name of the model to use. If factory is not provided, this is used to
create the model.

`factory` str \| NotGiven \| None  
Factory function to create the model instance.

`role` str \| NotGiven \| None  
Optional named role for model (e.g. for roles specified at the task or
eval level). Provide a default as a fallback in the case where the role
hasn’t been externally specified.

`default` str \| NotGiven \| None  
Optional. Fallback model in case the specified model or role is not
found. Should be a fully qualified model name (e.g. `openai/gpt-4o`).

`config` GenerateConfig \| NotGiven \| None  
Configuration for model. Config values will be override settings on the
`FlowTask` and `FlowSpec`.

`base_url` str \| NotGiven \| None  
Optional. Alternate base URL for model.

`api_key` str \| NotGiven \| None  
Optional. API key for model.

`memoize` bool \| NotGiven \| None  
Use/store a cached version of the model based on the parameters to
`get_model()`. Defaults to `True`.

`model_args` Mapping\[str, Any\] \| NotGiven \| None  
Additional args to pass to model constructor.

`flow_metadata` Mapping\[str, Any\] \| NotGiven \| None  
Optional. Metadata stored in the flow config. Not passed to the model.

### solvers_matrix

Create a list of solvers from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L288)

``` python
def solvers_matrix(
    *,
    solver: str | FlowSolver | Sequence[str | FlowSolver],
    args: Sequence[Mapping[str, Any] | NotGiven | None] | None = ...,
) -> list[FlowSolver]
```

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver)\]  
The solver or list of solvers to matrix.

`args` Sequence\[Mapping\[str, Any\] \| NotGiven \| None\] \| None  
Additional args to pass to solver constructor.

### solvers_with

Set fields on a list of solvers.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L217)

``` python
def solvers_with(
    *,
    solver: str | FlowSolver | Sequence[str | FlowSolver],
    name: str | NotGiven | None = ...,
    factory: str | NotGiven | None = ...,
    args: Mapping[str, Any] | NotGiven | None = ...,
    flow_metadata: Mapping[str, Any] | NotGiven | None = ...,
) -> list[FlowSolver]
```

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver)\]  
The solver or list of solvers to set fields on.

`name` str \| NotGiven \| None  
Name of the solver. Used to create the solver if the factory is not
provided.

`factory` str \| NotGiven \| None  
Factory function to create the solver instance.

`args` Mapping\[str, Any\] \| NotGiven \| None  
Additional args to pass to solver constructor.

`flow_metadata` Mapping\[str, Any\] \| NotGiven \| None  
Optional. Metadata stored in the flow config. Not passed to the solver.

### tasks_matrix

Create a list of tasks from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L302)

``` python
def tasks_matrix(
    *,
    task: str | FlowTask | Sequence[str | FlowTask],
    args: Sequence[Mapping[str, Any] | NotGiven | None] | None = ...,
    solver: Sequence[str | FlowSolver | FlowAgent | Solver | Agent | Sequence[str | FlowSolver | Solver] | NotGiven | None] | None = ...,
    model: Sequence[str | FlowModel | Model | NotGiven | None] | None = ...,
    config: Sequence[GenerateConfig | NotGiven] | None = ...,
    model_roles: Sequence[Mapping[str, FlowModel | str | Model] | NotGiven | None] | None = ...,
    message_limit: Sequence[int | NotGiven | None] | None = ...,
    token_limit: Sequence[int | NotGiven | None] | None = ...,
    time_limit: Sequence[int | NotGiven | None] | None = ...,
    working_limit: Sequence[int | NotGiven | None] | None = ...,
    cost_limit: Sequence[float | NotGiven | None] | None = ...,
) -> list[FlowTask]
```

`task` str \| [FlowTask](inspect_flow.qmd#flowtask) \| Sequence\[str \| [FlowTask](inspect_flow.qmd#flowtask)\]  
The task or list of tasks to matrix.

`args` Sequence\[Mapping\[str, Any\] \| NotGiven \| None\] \| None  
Additional args to pass to task constructor

`solver` Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| [FlowAgent](inspect_flow.qmd#flowagent) \| Solver \| Agent \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Solver\] \| NotGiven \| None\] \| None  
Solver or list of solvers. Defaults to `generate()`, a normal call to
the model.

`model` Sequence\[str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Model \| NotGiven \| None\] \| None  
Default model for task (Optional, defaults to eval model).

`config` Sequence\[GenerateConfig \| NotGiven\] \| None  
Model generation config for default model (does not apply to model
roles). Will override config settings on the `FlowSpec`. Will be
overridden by settings on the `FlowModel`.

`model_roles` Sequence\[Mapping\[str, [FlowModel](inspect_flow.qmd#flowmodel) \| str \| Model\] \| NotGiven \| None\] \| None  
Named roles for use in `get_model()`.

`message_limit` Sequence\[int \| NotGiven \| None\] \| None  
Limit on total messages used for each sample.

`token_limit` Sequence\[int \| NotGiven \| None\] \| None  
Limit on total tokens used for each sample.

`time_limit` Sequence\[int \| NotGiven \| None\] \| None  
Limit on clock time (in seconds) for samples.

`working_limit` Sequence\[int \| NotGiven \| None\] \| None  
Limit on working time (in seconds) for sample. Working time includes
model generation, tool calls, etc. but does not include time spent
waiting on retries or shared resources.

`cost_limit` Sequence\[float \| NotGiven \| None\] \| None  
Limit on total cost (in dollars) for each sample. Requires model cost
data via model_cost_config.

### tasks_with

Set fields on a list of tasks.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c/src/inspect_flow/_types/factories.py#L231)

``` python
def tasks_with(
    *,
    task: str | FlowTask | Sequence[str | FlowTask],
    name: str | NotGiven | None = ...,
    factory: str | NotGiven | None = ...,
    args: Mapping[str, Any] | NotGiven | None = ...,
    extra_args: FlowExtraArgs | NotGiven | None = ...,
    solver: str | FlowSolver | FlowAgent | Solver | Agent | Sequence[str | FlowSolver | Solver] | NotGiven | None = ...,
    scorer: str | FlowScorer | Scorer | Sequence[str | FlowScorer | Scorer] | NotGiven | None = ...,
    model: str | FlowModel | Model | NotGiven | None = ...,
    config: GenerateConfig | NotGiven = ...,
    model_roles: Mapping[str, FlowModel | str | Model] | NotGiven | None = ...,
    sandbox: str | tuple[str, str] | SandboxEnvironmentSpec | NotGiven | None = ...,
    approval: str | ApprovalPolicyConfig | NotGiven | None = ...,
    epochs: int | FlowEpochs | NotGiven | None = ...,
    fail_on_error: bool | float | NotGiven | None = ...,
    continue_on_fail: bool | NotGiven | None = ...,
    message_limit: int | NotGiven | None = ...,
    token_limit: int | NotGiven | None = ...,
    time_limit: int | NotGiven | None = ...,
    working_limit: int | NotGiven | None = ...,
    cost_limit: float | NotGiven | None = ...,
    early_stopping: NotGiven | None = ...,
    version: int | str | NotGiven = ...,
    tags: Sequence[str] | NotGiven | None = ...,
    metadata: Mapping[str, Any] | NotGiven | None = ...,
    sample_id: str | int | Sequence[str | int] | NotGiven | None = ...,
    flow_metadata: Mapping[str, Any] | NotGiven | None = ...,
) -> list[FlowTask]
```

`task` str \| [FlowTask](inspect_flow.qmd#flowtask) \| Sequence\[str \| [FlowTask](inspect_flow.qmd#flowtask)\]  
The task or list of tasks to set fields on.

`name` str \| NotGiven \| None  
Task name. Any of registry name (`"inspect_evals/mbpp"`), file name
(`"./my_task.py"`), or a file name and attr
(`"./my_task.py@task_name"`). Used to create the task if the factory is
not provided.

`factory` str \| NotGiven \| None  
Factory function to create the task instance.

`args` Mapping\[str, Any\] \| NotGiven \| None  
Additional args to pass to task constructor

`extra_args` FlowExtraArgs \| NotGiven \| None  
Extra args to provide to creation of inspect objects for this task. Will
override args provided in the `args` field on the `FlowModel`,
`FlowSolver`, `FlowScorer`, and `FlowAgent`.

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| [FlowAgent](inspect_flow.qmd#flowagent) \| Solver \| Agent \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Solver\] \| NotGiven \| None  
Solver or list of solvers. Defaults to `generate()`, a normal call to
the model.

`scorer` str \| [FlowScorer](inspect_flow.qmd#flowscorer) \| Scorer \| Sequence\[str \| [FlowScorer](inspect_flow.qmd#flowscorer) \| Scorer\] \| NotGiven \| None  
Scorer or list of scorers used to evaluate model output.

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Model \| NotGiven \| None  
Default model for task (Optional, defaults to eval model).

`config` GenerateConfig \| NotGiven  
Model generation config for default model (does not apply to model
roles). Will override config settings on the `FlowSpec`. Will be
overridden by settings on the `FlowModel`.

`model_roles` Mapping\[str, [FlowModel](inspect_flow.qmd#flowmodel) \| str \| Model\] \| NotGiven \| None  
Named roles for use in `get_model()`.

`sandbox` str \| tuple\[str, str\] \| SandboxEnvironmentSpec \| NotGiven \| None  
Sandbox environment type (or optionally a str or tuple with a shorthand
spec)

`approval` str \| ApprovalPolicyConfig \| NotGiven \| None  
Tool use approval policies. Either a path to an approval policy config
file or an approval policy config. Defaults to no approval policy.

`epochs` int \| [FlowEpochs](inspect_flow.qmd#flowepochs) \| NotGiven \| None  
Epochs to repeat samples for and optional score reducer function(s) used
to combine sample scores (defaults to `"mean"`)

`fail_on_error` bool \| float \| NotGiven \| None  
`True` to fail on first sample error (default); `False` to never fail on
sample errors; Value between 0 and 1 to fail if a proportion of total
samples fails. Value greater than 1 to fail eval if a count of samples
fails.

`continue_on_fail` bool \| NotGiven \| None  
`True` to continue running and only fail at the end if the
`fail_on_error` condition is met. `False` to fail eval immediately when
the `fail_on_error` condition is met (default).

`message_limit` int \| NotGiven \| None  
Limit on total messages used for each sample.

`token_limit` int \| NotGiven \| None  
Limit on total tokens used for each sample.

`time_limit` int \| NotGiven \| None  
Limit on clock time (in seconds) for samples.

`working_limit` int \| NotGiven \| None  
Limit on working time (in seconds) for sample. Working time includes
model generation, tool calls, etc. but does not include time spent
waiting on retries or shared resources.

`cost_limit` float \| NotGiven \| None  
Limit on total cost (in dollars) for each sample. Requires model cost
data via model_cost_config.

`early_stopping` NotGiven \| None  
Early stopping callbacks.

`version` int \| str \| NotGiven  
Version of task (to distinguish evolutions of the task spec or breaking
changes to it)

`tags` Sequence\[str\] \| NotGiven \| None  
Tags to associate with the task.

`metadata` Mapping\[str, Any\] \| NotGiven \| None  
Additional metadata to associate with the task.

`sample_id` str \| int \| Sequence\[str \| int\] \| NotGiven \| None  
Evaluate specific sample(s) from the dataset.

`flow_metadata` Mapping\[str, Any\] \| NotGiven \| None  
Optional. Metadata stored in the flow config. Not passed to the task.
