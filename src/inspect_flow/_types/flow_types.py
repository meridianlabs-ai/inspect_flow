# Type definitions for flow config files.

# Important: All default values should be None. This supports merging of partial configs as None values are not merged.
# But a different default value would override more specific settings.

from typing import (
    Any,
    Literal,
    Mapping,
    Sequence,
    TypeAlias,
)

from inspect_ai.approval._policy import ApprovalPolicyConfig
from inspect_ai.model import GenerateConfig
from inspect_ai.util import (
    DisplayType,
    SandboxEnvironmentType,
)
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self, override

CreateArgs: TypeAlias = Mapping[str, Any]
ModelRolesConfig: TypeAlias = Mapping[str, "FlowModel | str"]


class NotGiven(BaseModel, extra="forbid"):
    """For parameters with a meaningful None value, we need to distinguish between the user explicitly passing None, and the user not passing the parameter at all.

    User code shouldn't need to use not_given directly.
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"

    type: Literal["NOT_GIVEN"] = Field(
        description="Field to ensure serialized type can be identified as NotGiven",
    )


not_given = NotGiven(type="NOT_GIVEN")


class FlowModel(BaseModel, extra="forbid"):
    """Configuration for a Model."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the model to use. Required to be set by the time the model is created.",
    )

    role: str | None | NotGiven = Field(
        default=not_given,
        description="Optional named role for model (e.g. for roles specified at the task or eval level). Provide a default as a fallback in the case where the role hasn't been externally specified.",
    )

    default: str | None | NotGiven = Field(
        default=not_given,
        description="Optional. Fallback model in case the specified model or role is not found. Should be a fully qualified model name (e.g. openai/gpt-4o).",
    )

    config: GenerateConfig | None | NotGiven = Field(
        default=not_given,
        description="Configuration for model. Config values will be override settings on the FlowTask and FlowSpec.",
    )

    base_url: str | None | NotGiven = Field(
        default=not_given,
        description="Optional. Alternate base URL for model.",
    )

    api_key: str | None | NotGiven = Field(
        default=not_given,
        description="Optional. API key for model.",
    )

    memoize: bool | None | NotGiven = Field(
        default=not_given,
        description="Use/store a cached version of the model based on the parameters to get_model(). Defaults to True.",
    )

    model_args: CreateArgs | None | NotGiven = Field(
        default=not_given, description="Additional args to pass to model constructor."
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the model.",
    )


class FlowScorer(BaseModel, extra="forbid"):
    """Configuration for a Scorer."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the scorer. Required to be set by the time the scorer is created.",
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to scorer constructor.",
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the scorer.",
    )


class FlowSolver(BaseModel, extra="forbid"):
    """Configuration for a Solver."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the solver. Required to be set by the time the solver is created.",
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to solver constructor.",
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the solver.",
    )


class FlowAgent(BaseModel, extra="forbid"):
    """Configuration for an Agent."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the agent. Required to be set by the time the agent is created.",
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to agent constructor.",
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the agent.",
    )

    type: Literal["agent"] | None = Field(
        default=None,
        description="Type needed to differentiated solvers and agents in solver lists.",
    )

    @model_validator(mode="after")
    def set_type(self) -> Self:
        self.type = "agent"
        return self


class FlowEpochs(BaseModel, extra="forbid"):
    """Configuration for task epochs.

    Number of epochs to repeat samples over and optionally one or more
    reducers used to combine scores from samples across epochs. If not
    specified the "mean" score reducer is used.
    """

    epochs: int = Field(description="Number of epochs.")

    reducer: str | Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description='One or more reducers used to combine scores from samples across epochs (defaults to "mean")',
    )


class FlowTask(BaseModel, extra="forbid"):
    """Configuration for an evaluation task.

    Tasks are the basis for defining and running evaluations.
    """

    name: str | None | NotGiven = Field(
        default=not_given,
        description='Task name. Any of registry name ("inspect_evals/mbpp"), file name ("./my_task.py"), or a file name and attr ("./my_task.py@task_name"). Required to be set by the time the task is created.',
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to task constructor",
    )

    solver: (
        str | FlowSolver | Sequence[str | FlowSolver] | FlowAgent | None | NotGiven
    ) = Field(
        default=not_given,
        description="Solver or list of solvers. Defaults to generate(), a normal call to the model.",
    )

    scorer: str | FlowScorer | Sequence[str | FlowScorer] | None | NotGiven = Field(
        default=not_given,
        description="Scorer or list of scorers used to evaluate model output.",
    )

    model: str | FlowModel | None | NotGiven = Field(
        default=not_given,
        description="Default model for task (Optional, defaults to eval model).",
    )

    config: GenerateConfig | NotGiven = Field(
        default=not_given,
        description="Model generation config for default model (does not apply to model roles). Will override config settings on the FlowSpec. Will be overridden by settings on the FlowModel.",
    )

    model_roles: ModelRolesConfig | None | NotGiven = Field(
        default=not_given,
        description="Named roles for use in `get_model()`.",
    )

    sandbox: SandboxEnvironmentType | None | NotGiven = Field(
        default=not_given,
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec)",
    )

    approval: str | ApprovalPolicyConfig | None | NotGiven = Field(
        default=not_given,
        description="Tool use approval policies. Either a path to an approval policy config file or an approval policy config. Defaults to no approval policy.",
    )

    epochs: int | FlowEpochs | None | NotGiven = Field(
        default=not_given,
        description='Epochs to repeat samples for and optional score reducer function(s) used to combine sample scores (defaults to "mean")',
    )

    fail_on_error: bool | float | None | NotGiven = Field(
        default=not_given,
        description="`True` to fail on first sample error (default); `False` to never fail on sample errors; Value between 0 and 1 to fail if a proportion of total samples fails. Value greater than 1 to fail eval if a count of samples fails.",
    )

    continue_on_fail: bool | None | NotGiven = Field(
        default=not_given,
        description="`True` to continue running and only fail at the end if the `fail_on_error` condition is met. `False` to fail eval immediately when the `fail_on_error` condition is met (default).",
    )

    message_limit: int | None | NotGiven = Field(
        default=not_given, description="Limit on total messages used for each sample."
    )

    token_limit: int | None | NotGiven = Field(
        default=not_given, description="Limit on total tokens used for each sample."
    )

    time_limit: int | None | NotGiven = Field(
        default=not_given, description="Limit on clock time (in seconds) for samples."
    )

    working_limit: int | None | NotGiven = Field(
        default=not_given,
        description="Limit on working time (in seconds) for sample. Working time includes model generation, tool calls, etc. but does not include time spent waiting on retries or shared resources.",
    )

    version: int | str | NotGiven = Field(
        default=not_given,
        description="Version of task (to distinguish evolutions of the task spec or breaking changes to it)",
    )

    metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given, description="Additional metadata to associate with the task."
    )

    sample_id: str | int | Sequence[str | int] | None | NotGiven = Field(
        default=not_given,
        description="Evaluate specific sample(s) from the dataset.",
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the task.",
    )

    @property
    def model_name(self) -> str | None | NotGiven:
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

    retry_attempts: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of retry attempts before giving up (defaults to 10).",
    )

    retry_wait: float | None | NotGiven = Field(
        default=not_given,
        description="Time to wait between attempts, increased exponentially (defaults to 30, resulting in waits of 30, 60, 120, 240, etc.). Wait time per-retry will in no case be longer than 1 hour.",
    )

    retry_connections: float | None | NotGiven = Field(
        default=not_given,
        description="Reduce max_connections at this rate with each retry (defaults to 1.0, which results in no reduction).",
    )

    retry_cleanup: bool | None | NotGiven = Field(
        default=not_given,
        description="Cleanup failed log files after retries (defaults to True).",
    )

    sandbox: SandboxEnvironmentType | None | NotGiven = Field(
        default=not_given,
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec).",
    )

    sandbox_cleanup: bool | None | NotGiven = Field(
        default=not_given,
        description="Cleanup sandbox environments after task completes (defaults to True).",
    )

    tags: Sequence[str] | None | NotGiven = Field(
        default=not_given, description="Tags to associate with this evaluation run."
    )

    metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given, description="Metadata to associate with this evaluation run."
    )

    trace: bool | None | NotGiven = Field(
        default=not_given,
        description="Trace message interactions with evaluated model to terminal.",
    )

    display: DisplayType | None | NotGiven = Field(
        default=not_given, description="Task display type (defaults to 'full')."
    )

    approval: str | ApprovalPolicyConfig | None | NotGiven = Field(
        default=not_given,
        description="Tool use approval policies. Either a path to an approval policy config file or a list of approval policies. Defaults to no approval policy.",
    )

    score: bool | None | NotGiven = Field(
        default=not_given, description="Score output (defaults to True)."
    )

    log_level: str | None | NotGiven = Field(
        default=not_given,
        description='Level for logging to the console: "debug", "http", "sandbox", "info", "warning", "error", "critical", or "notset" (defaults to "warning").',
    )

    log_level_transcript: str | None | NotGiven = Field(
        default=not_given,
        description='Level for logging to the log file (defaults to "info").',
    )

    log_format: Literal["eval", "json"] | None | NotGiven = Field(
        default=not_given,
        description='Format for writing log files (defaults to "eval", the native high-performance format).',
    )

    limit: int | None | NotGiven = Field(
        default=not_given,
        description="Limit evaluated samples (defaults to all samples).",
    )

    sample_shuffle: bool | int | None | NotGiven = Field(
        default=not_given,
        description="Shuffle order of samples (pass a seed to make the order deterministic).",
    )

    fail_on_error: bool | float | None | NotGiven = Field(
        default=not_given,
        description="`True` to fail on first sample error(default); `False` to never fail on sample errors; Value between 0 and 1 to fail if a proportion of total samples fails. Value greater than 1 to fail eval if a count of samples fails.",
    )

    continue_on_fail: bool | None | NotGiven = Field(
        default=not_given,
        description="`True` to continue running and only fail at the end if the `fail_on_error` condition is met. `False` to fail eval immediately when the `fail_on_error` condition is met (default).",
    )

    retry_on_error: int | None | NotGiven = Field(
        default=not_given,
        description="Number of times to retry samples if they encounter errors (defaults to 3).",
    )

    debug_errors: bool | None | NotGiven = Field(
        default=not_given,
        description="Raise task errors (rather than logging them) so they can be debugged (defaults to False).",
    )

    max_samples: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of samples to run in parallel (default is max_connections).",
    )

    max_tasks: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of tasks to run in parallel (defaults is 10).",
    )

    max_subprocesses: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of subprocesses to run in parallel (default is os.cpu_count()).",
    )

    max_sandboxes: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of sandboxes (per-provider) to run in parallel.",
    )

    log_samples: bool | None | NotGiven = Field(
        default=not_given,
        description="Log detailed samples and scores (defaults to True).",
    )

    log_realtime: bool | None | NotGiven = Field(
        default=not_given,
        description="Log events in realtime (enables live viewing of samples in inspect view) (defaults to True).",
    )

    log_images: bool | None | NotGiven = Field(
        default=not_given,
        description="Log base64 encoded version of images, even if specified as a filename or URL (defaults to False).",
    )

    log_buffer: int | None | NotGiven = Field(
        default=not_given,
        description="Number of samples to buffer before writing log file. If not specified, an appropriate default for the format and filesystem is chosen (10 for most all cases, 100 for JSON logs on remote filesystems).",
    )

    log_shared: bool | int | None | NotGiven = Field(
        default=not_given,
        description="Sync sample events to log directory so that users on other systems can see log updates in realtime (defaults to no syncing). Specify `True` to sync every 10 seconds, otherwise an integer to sync every `n` seconds.",
    )

    bundle_dir: str | None | NotGiven = Field(
        default=not_given,
        description="If specified, the log viewer and logs generated by this eval set will be bundled into this directory. Relative paths will be resolved relative to the config file (when using the CLI) or base_dir arg (when using the API).",
    )

    bundle_overwrite: bool | None | NotGiven = Field(
        default=not_given,
        description="Whether to overwrite files in the bundle_dir. (defaults to False).",
    )

    log_dir_allow_dirty: bool | None | NotGiven = Field(
        default=not_given,
        description="If True, allow the log directory to contain unrelated logs. If False, ensure that the log directory only contains logs for tasks in this eval set (defaults to False).",
    )

    eval_set_id: str | None | NotGiven = Field(
        default=not_given,
        description="ID for the eval set. If not specified, a unique ID will be generated.",
    )

    bundle_url_mappings: dict[str, str] | None | NotGiven = Field(
        default=not_given,
        description="Replacements applied to bundle_dir to generate a URL. If provided and bundle_dir is set, the mapped URL will be written to stdout.",
    )


class FlowDefaults(BaseModel, extra="forbid"):
    """Default field values for Inspect objects. Will be overriden by more specific settings."""

    config: GenerateConfig | None | NotGiven = Field(
        default=not_given,
        description="Default model generation options. Will be overriden by settings on the FlowModel and FlowTask.",
    )

    agent: FlowAgent | None | NotGiven = Field(
        default=not_given, description="Field defaults for agents."
    )

    agent_prefix: dict[str, FlowAgent] | None | NotGiven = Field(
        default=not_given,
        description="Agent defaults for agent name prefixes. E.g. {'inspect/': FAgent(...)}",
    )

    model: FlowModel | None | NotGiven = Field(
        default=not_given, description="Field defaults for models."
    )

    model_prefix: dict[str, FlowModel] | None | NotGiven = Field(
        default=not_given,
        description="Model defaults for model name prefixes. E.g. {'openai/': FModel(...)}",
    )

    solver: FlowSolver | None | NotGiven = Field(
        default=not_given, description="Field defaults for solvers."
    )

    solver_prefix: dict[str, FlowSolver] | None | NotGiven = Field(
        default=not_given,
        description="Solver defaults for solver name prefixes. E.g. {'inspect/': FSolver(...)}",
    )

    task: FlowTask | None | NotGiven = Field(
        default=not_given, description="Field defaults for tasks."
    )

    task_prefix: dict[str, FlowTask] | None | NotGiven = Field(
        default=not_given,
        description="Task defaults for task name prefixes. E.g. {'inspect_evals/': FTask(...)}",
    )


class FlowDependencies(BaseModel, extra="forbid"):
    """Configuration for flow dependencies to install in the venv."""

    dependency_file: Literal["auto", "no_file"] | str | None | NotGiven = Field(
        default=not_given,
        description="Path to a dependency file (either requirements.txt or pyproject.toml) to use to create the virtual environment. If 'auto', will search the path starting from the same directory as the config file (when using the CLI) or base_dir arg (when using the API) looking for pyproject.toml or requirements.txt files. If 'no_file', no dependency file will be used. Defaults to 'auto'.",
    )

    additional_dependencies: str | Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description="Dependencies to pip install. E.g. PyPI package specifiers or Git repository URLs.",
    )

    auto_detect_dependencies: bool | None | NotGiven = Field(
        default=not_given,
        description="If True, automatically detect and install dependencies from names of objects in the config (defaults to True). For example, if a model name starts with 'openai/', the 'openai' package will be installed. If a task name is 'inspect_evals/mmlu' then the 'inspect-evals' package will be installed.",
    )

    uv_sync_args: str | Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description="Additional arguments to pass to 'uv sync' when creating the virtual environment using a pyproject.toml file. May be a string ('--dev --extra test') or a list of strings (['--dev', '--extra', 'test']).",
    )


class FlowSpec(BaseModel, extra="forbid"):
    """Top-level flow specification."""

    includes: Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description="List of other flow configs to include. Relative paths will be resolved relative to the config file (when using the CLI) or base_dir arg (when using the API). In addition to this list of explicit files to include, any _flow.py files in the same directory or any parent directory of the config file (when using the CLI) or base_dir arg (when using the API) will also be included automatically.",
    )

    log_dir: str | None | NotGiven = Field(
        default=not_given,
        description="Output path for logging results (required to ensure that a unique storage scope is assigned). Must be set before running the flow spec. Relative paths will be resolved relative to the config file (when using the CLI) or base_dir arg (when using the API).",
    )

    log_dir_create_unique: bool | None | NotGiven = Field(
        default=not_given,
        description="If True, create a new log directory by appending an _ and numeric suffix if the specified log_dir already exists. If the directory exists and has a _numeric suffix, that suffix will be incremented. If False, use the existing log_dir (which must be empty or have log_dir_allow_dirty=True). Defaults to False.",
    )

    python_version: str | None | NotGiven = Field(
        default=not_given,
        description="Python version to use in the flow virtual environment (e.g. '3.11')",
    )

    options: FlowOptions | None | NotGiven = Field(
        default=not_given, description="Arguments for calls to eval_set."
    )

    dependencies: FlowDependencies | None | NotGiven = Field(
        default=not_given,
        description="Dependencies to install in the venv. Defaults to auto-detecting dependencies from pyproject.toml, requirements.txt, and object names in the config.",
    )

    env: dict[str, str] | None | NotGiven = Field(
        default=not_given,
        description="Environment variables to set when running tasks.",
    )

    defaults: FlowDefaults | None | NotGiven = Field(
        default=not_given, description="Defaults values for Inspect objects."
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the model.",
    )

    tasks: Sequence[str | FlowTask] | None | NotGiven = Field(
        default=not_given, description="Tasks to run"
    )
