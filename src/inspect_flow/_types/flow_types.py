# Type definitions for flow config files.

# Important: All default values should be None. This supports merging of partial configs as None values are not merged.
# But a different default value would override more specific settings.

from typing import (
    Any,
    Literal,
    Mapping,
    Sequence,
    TypeAlias,
    TypeVar,
    overload,
)

from inspect_ai.approval._policy import ApprovalPolicyConfig
from inspect_ai.model import GenerateConfig
from inspect_ai.util import (
    DisplayType,
    SandboxEnvironmentType,
)
from pydantic import BaseModel, Field, field_validator

from inspect_flow._util.list_util import ensure_list_or_none

CreateArgs: TypeAlias = Mapping[str, Any]
ModelRolesConfig: TypeAlias = Mapping[str, "FlowModel | str"]


class FlowGenerateConfig(GenerateConfig, extra="forbid"):
    """Model generation options."""

    pass


class FlowModel(BaseModel, extra="forbid"):
    """Configuration for a Model."""

    name: str | None = Field(
        default=None,
        description="Name of the model to use. Required to be set by the time the model is created.",
    )

    role: str | None = Field(
        default=None,
        description="Optional named role for model (e.g. for roles specified at the task or eval level). Provide a default as a fallback in the case where the role hasn't been externally specified.",
    )

    default: str | None = Field(
        default=None,
        description="Optional. Fallback model in case the specified model or role is not found. Should be a fully qualified model name (e.g. openai/gpt-4o).",
    )

    config: FlowGenerateConfig | None = Field(
        default=None,
        description="Configuration for model. Config values will be override settings on the FlowTask and FlowJob.",
    )

    base_url: str | None = Field(
        default=None,
        description="Optional. Alternate base URL for model.",
    )

    api_key: str | None = Field(
        default=None,
        description="Optional. API key for model.",
    )

    memoize: bool | None = Field(
        default=None,
        description="Use/store a cached version of the model based on the parameters to get_model(). Defaults to True.",
    )

    model_args: CreateArgs | None = Field(
        default=None, description="Additional args to pass to model constructor."
    )

    flow_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional. Metadata stored in the flow config. Not passed to the model.",
    )


class FlowSolver(BaseModel, extra="forbid"):
    """Configuration for a Solver."""

    name: str | None = Field(
        default=None,
        description="Name of the solver. Required to be set by the time the solver is created.",
    )

    args: CreateArgs | None = Field(
        default=None,
        description="Additional args to pass to solver constructor.",
    )

    flow_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional. Metadata stored in the flow config. Not passed to the solver.",
    )


class FlowAgent(BaseModel, extra="forbid"):
    """Configuration for an Agent."""

    name: str | None = Field(
        default=None,
        description="Name of the agent. Required to be set by the time the agent is created.",
    )
    """Name of the agent. Required to be set by the time the agent is created."""

    args: CreateArgs | None = Field(
        default=None,
        description="Additional args to pass to agent constructor.",
    )

    flow_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional. Metadata stored in the flow config. Not passed to the agent.",
    )

    type: Literal["agent"] = Field(
        default="agent",
        description="Type needed to differentiated solvers and agents in solver lists.",
    )


class FlowEpochs(BaseModel):
    """Configuration for task epochs.

    Number of epochs to repeat samples over and optionally one or more
    reducers used to combine scores from samples across epochs. If not
    specified the "mean" score reducer is used.
    """

    epochs: int = Field(description="Number of epochs.")

    reducer: str | list[str] | None = Field(
        default=None,
        description='One or more reducers used to combine scores from samples across epochs (defaults to "mean")',
    )


class FlowTask(BaseModel, extra="forbid"):
    """Configuration for an evaluation task.

    Tasks are the basis for defining and running evaluations.
    """

    name: str | None = Field(
        default=None,
        description='Task name. Any of registry name ("inspect_evals/mbpp"), file name ("./my_task.py"), or a file name and attr ("./my_task.py@task_name"). Required to be set by the time the task is created.',
    )

    args: CreateArgs | None = Field(
        default=None,
        description="Additional args to pass to task constructor",
    )

    solver: str | FlowSolver | list[str | FlowSolver] | FlowAgent | None = Field(
        default=None,
        description="Solver or list of solvers. Defaults to generate(), a normal call to the model.",
    )

    model: str | FlowModel | None = Field(
        default=None,
        description="Default model for task (Optional, defaults to eval model).",
    )

    config: FlowGenerateConfig | None = Field(
        default=None,
        description="Model generation config for default model (does not apply to model roles). Will override config settings on the FlowJob. Will be overridden by settings on the FlowModel.",
    )

    model_roles: ModelRolesConfig | None = Field(
        default=None,
        description="Named roles for use in `get_model()`.",
    )

    sandbox: SandboxEnvironmentType | None = Field(
        default=None,
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec)",
    )

    approval: str | ApprovalPolicyConfig | None = Field(
        default=None,
        description="Tool use approval policies. Either a path to an approval policy config file or an approval policy config. Defaults to no approval policy.",
    )

    epochs: int | FlowEpochs | None = Field(
        default=None,
        description='Epochs to repeat samples for and optional score reducer function(s) used to combine sample scores (defaults to "mean")',
    )

    fail_on_error: bool | float | None = Field(
        default=None,
        description="`True` to fail on first sample error (default); `False` to never fail on sample errors; Value between 0 and 1 to fail if a proportion of total samples fails. Value greater than 1 to fail eval if a count of samples fails.",
    )

    continue_on_fail: bool | None = Field(
        default=None,
        description="`True` to continue running and only fail at the end if the `fail_on_error` condition is met. `False` to fail eval immediately when the `fail_on_error` condition is met (default).",
    )

    message_limit: int | None = Field(
        default=None, description="Limit on total messages used for each sample."
    )

    token_limit: int | None = Field(
        default=None, description="Limit on total tokens used for each sample."
    )

    time_limit: int | None = Field(
        default=None, description="Limit on clock time (in seconds) for samples."
    )

    working_limit: int | None = Field(
        default=None,
        description="Limit on working time (in seconds) for sample. Working time includes model generation, tool calls, etc. but does not include time spent waiting on retries or shared resources.",
    )

    version: int | str | None = Field(
        default=None,
        description="Version of task (to distinguish evolutions of the task spec or breaking changes to it)",
    )

    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata to associate with the task."
    )

    sample_id: str | int | list[str | int] | None = Field(
        default=None,
        description="Evaluate specific sample(s) from the dataset.",
    )

    flow_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional. Metadata stored in the flow config. Not passed to the task.",
    )

    @field_validator("model", mode="before")
    @classmethod
    def convert_string_model(cls, v):
        return _convert_str_to_class(FlowModel, v)

    @field_validator("solver", mode="before")
    @classmethod
    def convert_string_solvers(cls, v):
        return _convert_str_to_solver(v)

    @property
    def model_name(self) -> str | None:
        """Get the model name from the model field.

        Returns:
            The model name if set, otherwise None.
        """
        if isinstance(self.model, str):
            return self.model
        elif isinstance(self.model, FlowModel):
            return self.model.name
        return None


class FlowOptions(BaseModel, extra="forbid"):
    """Evaluation options."""

    retry_attempts: int | None = Field(
        default=None,
        description="Maximum number of retry attempts before giving up (defaults to 10).",
    )

    retry_wait: float | None = Field(
        default=None,
        description="Time to wait between attempts, increased exponentially (defaults to 30, resulting in waits of 30, 60, 120, 240, etc.). Wait time per-retry will in no case be longer than 1 hour.",
    )

    retry_connections: float | None = Field(
        default=None,
        description="Reduce max_connections at this rate with each retry (defaults to 1.0, which results in no reduction).",
    )

    retry_cleanup: bool | None = Field(
        default=None,
        description="Cleanup failed log files after retries (defaults to True).",
    )

    sandbox: SandboxEnvironmentType | None = Field(
        default=None,
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec).",
    )

    sandbox_cleanup: bool | None = Field(
        default=None,
        description="Cleanup sandbox environments after task completes (defaults to True).",
    )

    tags: list[str] | None = Field(
        default=None, description="Tags to associate with this evaluation run."
    )

    metadata: dict[str, Any] | None = Field(
        default=None, description="Metadata to associate with this evaluation run."
    )

    trace: bool | None = Field(
        default=None,
        description="Trace message interactions with evaluated model to terminal.",
    )

    display: DisplayType | None = Field(
        default=None, description="Task display type (defaults to 'full')."
    )

    approval: str | ApprovalPolicyConfig | None = Field(
        default=None,
        description="Tool use approval policies. Either a path to an approval policy config file or a list of approval policies. Defaults to no approval policy.",
    )

    score: bool | None = Field(
        default=None, description="Score output (defaults to True)."
    )

    log_level: str | None = Field(
        default=None,
        description='Level for logging to the console: "debug", "http", "sandbox", "info", "warning", "error", "critical", or "notset" (defaults to "warning").',
    )

    log_level_transcript: str | None = Field(
        default=None,
        description='Level for logging to the log file (defaults to "info").',
    )

    log_format: Literal["eval", "json"] | None = Field(
        default=None,
        description='Format for writing log files (defaults to "eval", the native high-performance format).',
    )

    limit: int | None = Field(
        default=None, description="Limit evaluated samples (defaults to all samples)."
    )

    sample_shuffle: bool | int | None = Field(
        default=None,
        description="Shuffle order of samples (pass a seed to make the order deterministic).",
    )

    fail_on_error: bool | float | None = Field(
        default=None,
        description="`True` to fail on first sample error(default); `False` to never fail on sample errors; Value between 0 and 1 to fail if a proportion of total samples fails. Value greater than 1 to fail eval if a count of samples fails.",
    )

    continue_on_fail: bool | None = Field(
        default=None,
        description="`True` to continue running and only fail at the end if the `fail_on_error` condition is met. `False` to fail eval immediately when the `fail_on_error` condition is met (default).",
    )

    retry_on_error: int | None = Field(
        default=None,
        description="Number of times to retry samples if they encounter errors (defaults to 3).",
    )

    debug_errors: bool | None = Field(
        default=None,
        description="Raise task errors (rather than logging them) so they can be debugged (defaults to False).",
    )

    max_samples: int | None = Field(
        default=None,
        description="Maximum number of samples to run in parallel (default is max_connections).",
    )

    max_tasks: int | None = Field(
        default=None,
        description="Maximum number of tasks to run in parallel (defaults is 10).",
    )

    max_subprocesses: int | None = Field(
        default=None,
        description="Maximum number of subprocesses to run in parallel (default is os.cpu_count()).",
    )

    max_sandboxes: int | None = Field(
        default=None,
        description="Maximum number of sandboxes (per-provider) to run in parallel.",
    )

    log_samples: bool | None = Field(
        default=None, description="Log detailed samples and scores (defaults to True)."
    )

    log_realtime: bool | None = Field(
        default=None,
        description="Log events in realtime (enables live viewing of samples in inspect view) (defaults to True).",
    )

    log_images: bool | None = Field(
        default=None,
        description="Log base64 encoded version of images, even if specified as a filename or URL (defaults to False).",
    )

    log_buffer: int | None = Field(
        default=None,
        description="Number of samples to buffer before writing log file. If not specified, an appropriate default for the format and filesystem is chosen (10 for most all cases, 100 for JSON logs on remote filesystems).",
    )

    log_shared: bool | int | None = Field(
        default=None,
        description="Sync sample events to log directory so that users on other systems can see log updates in realtime (defaults to no syncing). Specify `True` to sync every 10 seconds, otherwise an integer to sync every `n` seconds.",
    )

    bundle_dir: str | None = Field(
        default=None,
        description="If specified, the log viewer and logs generated by this eval set will be bundled into this directory.",
    )

    bundle_overwrite: bool | None = Field(
        default=None,
        description="Whether to overwrite files in the bundle_dir. (defaults to False).",
    )

    log_dir_allow_dirty: bool | None = Field(
        default=None,
        description="If True, allow the log directory to contain unrelated logs. If False, ensure that the log directory only contains logs for tasks in this eval set (defaults to False).",
    )

    eval_set_id: str | None = Field(
        default=None,
        description="ID for the eval set. If not specified, a unique ID will be generated.",
    )

    bundle_url_map: dict[str, str] | None = Field(
        default=None,
        description="Replacements applied to bundle_dir to generate a URL. If provided and bundle_dir is set, the mapped URL will be written to stdout.",
    )


class FlowDefaults(BaseModel, extra="forbid"):
    """Default field values for Inspect objects. Will be overriden by more specific settings."""

    config: FlowGenerateConfig | None = Field(
        default=None,
        description="Default model generation options. Will be overriden by settings on the FlowModel and FlowTask.",
    )

    agent: FlowAgent | None = Field(
        default=None, description="Field defaults for agents."
    )

    agent_prefix: dict[str, FlowAgent] | None = Field(
        default=None,
        description="Agent defaults for agent name prefixes. E.g. {'inspect/': FAgent(...)}",
    )

    model: FlowModel | None = Field(
        default=None, description="Field defaults for models."
    )

    model_prefix: dict[str, FlowModel] | None = Field(
        default=None,
        description="Model defaults for model name prefixes. E.g. {'openai/': FModel(...)}",
    )

    solver: FlowSolver | None = Field(
        default=None, description="Field defaults for solvers."
    )

    solver_prefix: dict[str, FlowSolver] | None = Field(
        default=None,
        description="Solver defaults for solver name prefixes. E.g. {'inspect/': FSolver(...)}",
    )

    task: FlowTask | None = Field(default=None, description="Field defaults for tasks.")

    task_prefix: dict[str, FlowTask] | None = Field(
        default=None,
        description="Task defaults for task name prefixes. E.g. {'inspect_evals/': FTask(...)}",
    )


class FlowInclude(BaseModel, extra="forbid"):
    """Configuration for including other flow configs."""

    config_file_path: str | None = Field(
        default=None, description="Path to the flow config to include."
    )


class FlowJob(BaseModel, extra="forbid"):
    """Configuration for a flow job."""

    includes: Sequence[str | FlowInclude] | None = Field(
        default=None,
        description="List of other flow configs to include.",
    )

    log_dir: str | None = Field(
        default=None,
        description="Output path for logging results (required to ensure that a unique storage scope is assigned). Must be set before running the flow job. If a relative path, it will be resolved relative to the most recent config file loaded with 'load_job' or the current working directory if 'load_job' was not used.",
    )

    log_dir_create_unique: bool | None = Field(
        default=None,
        description="If True, create a new log directory by appending an _ and numeric suffix if the specified log_dir already exists. If the directory exists and has a _numeric suffix, that suffix will be incremented. If False, use the existing log_dir (which must be empty or have log_dir_allow_dirty=True). Defaults to False.",
    )

    python_version: str | None = Field(
        default=None,
        description="Python version to use in the flow virtual environment (e.g. '3.11')",
    )

    options: FlowOptions | None = Field(
        default=None, description="Arguments for calls to eval_set."
    )

    dependencies: list[str] | None = Field(
        default=None,
        description="Dependencies to pip install. E.g. PyPI package specifiers or Git repository URLs.",
    )

    env: dict[str, str] | None = Field(
        default=None, description="Environment variables to set when running tasks."
    )

    defaults: FlowDefaults | None = Field(
        default=None, description="Defaults values for Inspect objects."
    )

    flow_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional. Metadata stored in the flow config. Not passed to the model.",
    )

    tasks: Sequence[str | FlowTask] | None = Field(
        default=None, description="Tasks to run"
    )

    # Convert single items to lists
    @field_validator("dependencies", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)

    @field_validator("tasks", mode="before")
    @classmethod
    def convert_string_tasks(cls, v):
        return _convert_to_task_list(v)

    @field_validator("includes", mode="before")
    @classmethod
    def convert_string_includes(cls, v):
        return _convert_to_include_list(v)


def _convert_to_task_list(
    v: str | FlowTask | list[str | FlowTask] | None,
) -> list[FlowTask] | None:
    if v is None:
        return v
    if not isinstance(v, list):
        v = [v]
    return [FlowTask(name=task) if isinstance(task, str) else task for task in v]


def _convert_to_include_list(
    v: str | FlowInclude | list[str | FlowInclude] | None,
) -> list[FlowInclude] | None:
    if v is None:
        return v
    if not isinstance(v, list):
        v = [v]
    return [
        FlowInclude(config_file_path=include) if isinstance(include, str) else include
        for include in v
    ]


_T = TypeVar("_T", FlowModel, FlowSolver)


@overload
def _convert_str_to_class(cls: type[_T], v: None) -> None: ...


@overload
def _convert_str_to_class(cls: type[_T], v: str | _T) -> _T: ...


def _convert_str_to_class(cls: type[_T], v: str | _T | None) -> _T | None:
    return cls(name=v) if isinstance(v, str) else v


def _convert_str_to_solver(
    v: str | FlowSolver | list[str | FlowSolver] | None,
) -> FlowSolver | list[FlowSolver] | None:
    if v is None:
        return None
    if isinstance(v, list):
        return [_convert_str_to_class(FlowSolver, solver) for solver in v]
    return _convert_str_to_class(FlowSolver, v)
