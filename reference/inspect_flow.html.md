# inspect_flow


## Types

### FlowAgent

Configuration for an Agent.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L179)

``` python
class FlowAgent(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the agent. Used to create the agent if the factory is not
provided.

`factory` Callable\[..., Agent\] \| None \| NotGiven  
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

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L567)

``` python
class FlowDefaults(FlowBase)
```

#### Attributes

`config` GenerateConfig \| None \| NotGiven  
Default model generation options. Will be overriden by settings on the
FlowModel and FlowTask.

`agent` [FlowAgent](inspect_flow.qmd#flowagent) \| None \| NotGiven  
Field defaults for agents.

`agent_prefix` dict\[str, [FlowAgent](inspect_flow.qmd#flowagent)\] \| None \| NotGiven  
Agent defaults for agent name prefixes. E.g. {‘inspect/’: FAgent(…)}

`model` [FlowModel](inspect_flow.qmd#flowmodel) \| None \| NotGiven  
Field defaults for models.

`model_prefix` dict\[str, [FlowModel](inspect_flow.qmd#flowmodel)\] \| None \| NotGiven  
Model defaults for model name prefixes. E.g. {‘openai/’: FModel(…)}

`solver` [FlowSolver](inspect_flow.qmd#flowsolver) \| None \| NotGiven  
Field defaults for solvers.

`solver_prefix` dict\[str, [FlowSolver](inspect_flow.qmd#flowsolver)\] \| None \| NotGiven  
Solver defaults for solver name prefixes. E.g. {‘inspect/’: FSolver(…)}

`task` [FlowTask](inspect_flow.qmd#flowtask) \| None \| NotGiven  
Field defaults for tasks.

`task_prefix` dict\[str, [FlowTask](inspect_flow.qmd#flowtask)\] \| None \| NotGiven  
Task defaults for task name prefixes. E.g. {‘inspect_evals/’: FTask(…)}

### FlowDependencies

Configuration for flow dependencies to install in the venv.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L612)

``` python
class FlowDependencies(FlowBase)
```

#### Attributes

`dependency_file` Literal\['auto', 'no_file'\] \| str \| None \| NotGiven  
Path to a dependency file (either requirements.txt or pyproject.toml) to
use to create the virtual environment. If ‘auto’, will search the path
starting from the same directory as the config file (when using the CLI)
or base_dir arg (when using the API) looking for pyproject.toml or
requirements.txt files. If ‘no_file’, no dependency file will be used.
Defaults to ‘auto’.

`additional_dependencies` str \| Sequence\[str\] \| None \| NotGiven  
Dependencies to pip install. E.g. PyPI package specifiers or Git
repository URLs.

`auto_detect_dependencies` bool \| None \| NotGiven  
If True, automatically detect and install dependencies from names of
objects in the config (defaults to True). For example, if a model name
starts with ‘openai/’, the ‘openai’ package will be installed. If a task
name is ‘inspect_evals/mmlu’ then the ‘inspect-evals’ package will be
installed.

`uv_sync_args` str \| Sequence\[str\] \| None \| NotGiven  
Additional arguments to pass to ‘uv sync’ when creating the virtual
environment using a pyproject.toml file. May be a string (‘–dev –extra
test’) or a list of strings (\[‘–dev’, ‘–extra’, ‘test’\]).

### FlowEpochs

Configuration for task epochs.

Number of epochs to repeat samples over and optionally one or more
reducers used to combine scores from samples across epochs. If not
specified the “mean” score reducer is used.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L213)

``` python
class FlowEpochs(FlowBase)
```

#### Attributes

`epochs` int  
Number of epochs.

`reducer` str \| Sequence\[str\] \| None \| NotGiven  
One or more reducers used to combine scores from samples across epochs
(defaults to “mean”)

### FlowSpec

Top-level flow specification.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L636)

``` python
class FlowSpec(FlowBase, arbitrary_types_allowed=True)
```

#### Attributes

`includes` Sequence\[str \| [FlowSpec](inspect_flow.qmd#flowspec)\] \| None \| NotGiven  
List of other flow specs to include. Relative paths will be resolved
relative to the config file (when using the CLI) or base_dir arg (when
using the API). In addition to this list of explicit files to include,
any \_flow.py files in the same directory or any parent directory of the
config file (when using the CLI) or base_dir arg (when using the API)
will also be included automatically.

`store` Literal\['auto'\] \| str \| None \| NotGiven  
Path to directory to use for flow storage. ‘auto’ will use a default
application location. None will disable storage. Relative paths will be
resolved relative to the config file (when using the CLI) or base_dir
arg (when using the API). If not given, ‘auto’ will be used.

`log_dir` str \| None \| NotGiven  
Output path for logging results (required to ensure that a unique
storage scope is assigned). Must be set before running the flow spec.
Relative paths will be resolved relative to the config file (when using
the CLI) or base_dir arg (when using the API).

`log_dir_create_unique` bool \| None \| NotGiven  
If True, create a new log directory by appending an \_ and numeric
suffix if the specified log_dir already exists. If the directory exists
and has a \_numeric suffix, that suffix will be incremented. If False,
use the existing log_dir (which must be empty or have
log_dir_allow_dirty=True). Defaults to False.

`execution_type` Literal\['inproc', 'venv'\] \| None \| NotGiven  
Execution environment for running tasks (defaults to ‘inproc’).

`python_version` str \| None \| NotGiven  
Python version to use in the flow virtual environment (e.g. ‘3.11’)

`dependencies` [FlowDependencies](inspect_flow.qmd#flowdependencies) \| None \| NotGiven  
Dependencies to install in the venv. Defaults to auto-detecting
dependencies from pyproject.toml, requirements.txt, and object names in
the config.

`options` [FlowOptions](inspect_flow.qmd#flowoptions) \| None \| NotGiven  
Arguments for calls to eval_set.

`env` dict\[str, str\] \| None \| NotGiven  
Environment variables to set when running tasks.

`defaults` [FlowDefaults](inspect_flow.qmd#flowdefaults) \| None \| NotGiven  
Defaults values for Inspect objects.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the model.

`tasks` Sequence\[str \| [FlowTask](inspect_flow.qmd#flowtask) \| Task\] \| None \| NotGiven  
Tasks to run

### FlowModel

Configuration for a Model.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L78)

``` python
class FlowModel(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the model to use. If factory is not provided, this is used to
create the model.

`factory` Callable\[..., Model\] \| None \| NotGiven  
Factory function to create the model instance.

`role` str \| None \| NotGiven  
Optional named role for model (e.g. for roles specified at the task or
eval level). Provide a default as a fallback in the case where the role
hasn’t been externally specified.

`default` str \| None \| NotGiven  
Optional. Fallback model in case the specified model or role is not
found. Should be a fully qualified model name (e.g. openai/gpt-4o).

`config` GenerateConfig \| None \| NotGiven  
Configuration for model. Config values will be override settings on the
FlowTask and FlowSpec.

`base_url` str \| None \| NotGiven  
Optional. Alternate base URL for model.

`api_key` str \| None \| NotGiven  
Optional. API key for model.

`memoize` bool \| None \| NotGiven  
Use/store a cached version of the model based on the parameters to
get_model(). Defaults to True.

`model_args` CreateArgs \| None \| NotGiven  
Additional args to pass to model constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the model.

### FlowOptions

Evaluation options.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L392)

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
Reduce max_connections at this rate with each retry (defaults to 1.0,
which results in no reduction).

`retry_cleanup` bool \| None \| NotGiven  
Cleanup failed log files after retries (defaults to True).

`sandbox` SandboxEnvironmentType \| None \| NotGiven  
Sandbox environment type (or optionally a str or tuple with a shorthand
spec).

`sandbox_cleanup` bool \| None \| NotGiven  
Cleanup sandbox environments after task completes (defaults to True).

`tags` Sequence\[str\] \| None \| NotGiven  
Tags to associate with this evaluation run.

`metadata` dict\[str, Any\] \| None \| NotGiven  
Metadata to associate with this evaluation run.

`trace` bool \| None \| NotGiven  
Trace message interactions with evaluated model to terminal.

`display` [DisplayType](inspect_flow.api.qmd#displaytype) \| None \| NotGiven  
Task display type (defaults to ‘full’).

`approval` str \| ApprovalPolicyConfig \| None \| NotGiven  
Tool use approval policies. Either a path to an approval policy config
file or a list of approval policies. Defaults to no approval policy.

`score` bool \| None \| NotGiven  
Score output (defaults to True).

`log_level` str \| None \| NotGiven  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”).

`log_level_transcript` str \| None \| NotGiven  
Level for logging to the log file (defaults to “info”).

`log_format` Literal\['eval', 'json'\] \| None \| NotGiven  
Format for writing log files (defaults to “eval”, the native
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
(defaults to False).

`max_samples` int \| None \| NotGiven  
Maximum number of samples to run in parallel (default is
max_connections).

`max_tasks` int \| None \| NotGiven  
Maximum number of tasks to run in parallel (defaults is 10).

`max_subprocesses` int \| None \| NotGiven  
Maximum number of subprocesses to run in parallel (default is
os.cpu_count()).

`max_sandboxes` int \| None \| NotGiven  
Maximum number of sandboxes (per-provider) to run in parallel.

`log_samples` bool \| None \| NotGiven  
Log detailed samples and scores (defaults to True).

`log_realtime` bool \| None \| NotGiven  
Log events in realtime (enables live viewing of samples in inspect view)
(defaults to True).

`log_images` bool \| None \| NotGiven  
Log base64 encoded version of images, even if specified as a filename or
URL (defaults to False).

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
the config file (when using the CLI) or base_dir arg (when using the
API).

`bundle_overwrite` bool \| None \| NotGiven  
Whether to overwrite files in the bundle_dir. (defaults to False).

`log_dir_allow_dirty` bool \| None \| NotGiven  
If True, allow the log directory to contain unrelated logs. If False,
ensure that the log directory only contains logs for tasks in this eval
set (defaults to False).

`eval_set_id` str \| None \| NotGiven  
ID for the eval set. If not specified, a unique ID will be generated.

`bundle_url_mappings` dict\[str, str\] \| None \| NotGiven  
Replacements applied to bundle_dir to generate a URL. If provided and
bundle_dir is set, the mapped URL will be written to stdout.

### FlowScorer

Configuration for a Scorer.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L131)

``` python
class FlowScorer(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the scorer. Used to create the scorer if the factory is not
provided.

`factory` Callable\[..., Scorer\] \| None \| NotGiven  
Factory function to create the scorer instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to scorer constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the scorer.

### FlowSolver

Configuration for a Solver.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L155)

``` python
class FlowSolver(FlowBase)
```

#### Attributes

`name` str \| None \| NotGiven  
Name of the solver. Used to create the solver if the factory is not
provided.

`factory` Callable\[..., Solver\] \| None \| NotGiven  
Factory function to create the solver instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to solver constructor.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the solver.

### FlowTask

Configuration for an evaluation task.

Tasks are the basis for defining and running evaluations.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/flow_types.py#L250)

``` python
class FlowTask(FlowBase, arbitrary_types_allowed=True)
```

#### Attributes

`name` str \| None \| NotGiven  
Task name. Any of registry name (“inspect_evals/mbpp”), file name
(“./my_task.py”), or a file name and attr (“./<my_task.py@task>\_name”).
Used to create the task if the factory is not provided.

`factory` Callable\[..., Task\] \| None \| NotGiven  
Factory function to create the task instance.

`args` CreateArgs \| None \| NotGiven  
Additional args to pass to task constructor

`extra_args` FlowExtraArgs \| None \| NotGiven  
Extra args to provide to creation of inspect objects for this task. Will
override args provided in the ‘args’ field on the FlowModel, FlowSolver,
FlowScorer, and FlowAgent.

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| [FlowAgent](inspect_flow.qmd#flowagent) \| Solver \| Agent \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Solver\] \| None \| NotGiven  
Solver or list of solvers. Defaults to generate(), a normal call to the
model.

`scorer` str \| [FlowScorer](inspect_flow.qmd#flowscorer) \| Scorer \| Sequence\[str \| [FlowScorer](inspect_flow.qmd#flowscorer) \| Scorer\] \| None \| NotGiven  
Scorer or list of scorers used to evaluate model output.

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Model \| None \| NotGiven  
Default model for task (Optional, defaults to eval model).

`config` GenerateConfig \| NotGiven  
Model generation config for default model (does not apply to model
roles). Will override config settings on the FlowSpec. Will be
overridden by settings on the FlowModel.

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
to combine sample scores (defaults to “mean”)

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

`version` int \| str \| NotGiven  
Version of task (to distinguish evolutions of the task spec or breaking
changes to it)

`metadata` dict\[str, Any\] \| None \| NotGiven  
Additional metadata to associate with the task.

`sample_id` str \| int \| Sequence\[str \| int\] \| None \| NotGiven  
Evaluate specific sample(s) from the dataset.

`flow_metadata` dict\[str, Any\] \| None \| NotGiven  
Optional. Metadata stored in the flow config. Not passed to the task.

`model_name` str \| None \| NotGiven  
Get the model name from the model field.

Returns: The model name if set, otherwise None.

## Decorators

### after_load

Decorator to mark a function to be called after a FlowSpec is loaded.

The decorated function should have the signature (args are all optional
and may be omitted): def after_flow_spec_loaded( spec: FlowSpec, files:
list\[str\], ) -\> None:

    spec: The loaded FlowSpec.
    files: List of file paths that were loaded to create the FlowSpec.

…

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/decorator.py#L9)

``` python
def after_load(func: F) -> F
```

`func` F  
The function to decorate.

## Functions

### agents_matrix

Create a list of agents from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L245)

``` python
def agents_matrix(
    *,
    agent: str | FlowAgent | Sequence[str | FlowAgent],
    **kwargs: Unpack[FlowAgentMatrixDict],
) -> list[FlowAgent]
```

`agent` str \| [FlowAgent](inspect_flow.qmd#flowagent) \| Sequence\[str \| [FlowAgent](inspect_flow.qmd#flowagent)\]  
The agent or list of agents to matrix.

`**kwargs` Unpack\[FlowAgentMatrixDict\]  
The lists of field values to matrix.

### agents_with

Set fields on a list of agents.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L175)

``` python
def agents_with(
    *,
    agent: str | FlowAgent | Sequence[str | FlowAgent],
    **kwargs: Unpack[FlowAgentDict],
) -> list[FlowAgent]
```

`agent` str \| [FlowAgent](inspect_flow.qmd#flowagent) \| Sequence\[str \| [FlowAgent](inspect_flow.qmd#flowagent)\]  
The agent or list of agents to set fields on.

`**kwargs` Unpack\[FlowAgentDict\]  
The fields to set on each agent.

### configs_matrix

Create a list of generate configs from the product of lists of field
values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L259)

``` python
def configs_matrix(
    *,
    config: GenerateConfig | Sequence[GenerateConfig] | None = None,
    **kwargs: Unpack[GenerateConfigMatrixDict],
) -> list[GenerateConfig]
```

`config` GenerateConfig \| Sequence\[GenerateConfig\] \| None  
The config or list of configs to matrix.

`**kwargs` Unpack\[GenerateConfigMatrixDict\]  
The lists of field values to matrix.

### configs_with

Set fields on a list of generate configs.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L189)

``` python
def configs_with(
    *,
    config: GenerateConfig | Sequence[GenerateConfig],
    **kwargs: Unpack[GenerateConfigDict],
) -> list[GenerateConfig]
```

`config` GenerateConfig \| Sequence\[GenerateConfig\]  
The config or list of configs to set fields on.

`**kwargs` Unpack\[GenerateConfigDict\]  
The fields to set on each config.

### merge

Merge two flow objects.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/merge.py#L52)

``` python
def merge(base: _T, add: _T) -> _T
```

`base` \_T  
The base object.

`add` \_T  
The object to merge into the base. Values in this object will override
those in the base.

### models_matrix

Create a list of models from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L274)

``` python
def models_matrix(
    *,
    model: str | FlowModel | Sequence[str | FlowModel],
    **kwargs: Unpack[FlowModelMatrixDict],
) -> list[FlowModel]
```

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Sequence\[str \| [FlowModel](inspect_flow.qmd#flowmodel)\]  
The model or list of models to matrix.

`**kwargs` Unpack\[FlowModelMatrixDict\]  
The lists of field values to matrix.

### models_with

Set fields on a list of models.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L203)

``` python
def models_with(
    *,
    model: str | FlowModel | Sequence[str | FlowModel],
    **kwargs: Unpack[FlowModelDict],
) -> list[FlowModel]
```

`model` str \| [FlowModel](inspect_flow.qmd#flowmodel) \| Sequence\[str \| [FlowModel](inspect_flow.qmd#flowmodel)\]  
The model or list of models to set fields on.

`**kwargs` Unpack\[FlowModelDict\]  
The fields to set on each model.

### solvers_matrix

Create a list of solvers from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L288)

``` python
def solvers_matrix(
    *,
    solver: str | FlowSolver | Sequence[str | FlowSolver],
    **kwargs: Unpack[FlowSolverMatrixDict],
) -> list[FlowSolver]
```

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver)\]  
The solver or list of solvers to matrix.

`**kwargs` Unpack\[FlowSolverMatrixDict\]  
The lists of field values to matrix.

### solvers_with

Set fields on a list of solvers.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L217)

``` python
def solvers_with(
    *,
    solver: str | FlowSolver | Sequence[str | FlowSolver],
    **kwargs: Unpack[FlowSolverDict],
) -> list[FlowSolver]
```

`solver` str \| [FlowSolver](inspect_flow.qmd#flowsolver) \| Sequence\[str \| [FlowSolver](inspect_flow.qmd#flowsolver)\]  
The solver or list of solvers to set fields on.

`**kwargs` Unpack\[FlowSolverDict\]  
The fields to set on each solver.

### tasks_matrix

Create a list of tasks from the product of lists of field values.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L302)

``` python
def tasks_matrix(
    *,
    task: str | FlowTask | Sequence[str | FlowTask],
    **kwargs: Unpack[FlowTaskMatrixDict],
) -> list[FlowTask]
```

`task` str \| [FlowTask](inspect_flow.qmd#flowtask) \| Sequence\[str \| [FlowTask](inspect_flow.qmd#flowtask)\]  
The task or list of tasks to matrix.

`**kwargs` Unpack\[FlowTaskMatrixDict\]  
The lists of field values to matrix.

### tasks_with

Set fields on a list of tasks.

[Source](https://github.com/meridianlabs-ai/inspect_flow/blob/959cf28d40855ec6024b7413113fa23dff29d079/src/inspect_flow/_types/factories.py#L231)

``` python
def tasks_with(
    *,
    task: str | FlowTask | Sequence[str | FlowTask],
    **kwargs: Unpack[FlowTaskDict],
) -> list[FlowTask]
```

`task` str \| [FlowTask](inspect_flow.qmd#flowtask) \| Sequence\[str \| [FlowTask](inspect_flow.qmd#flowtask)\]  
The task or list of tasks to set fields on.

`**kwargs` Unpack\[FlowTaskDict\]  
The fields to set on each task.
