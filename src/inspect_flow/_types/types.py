from typing import Any, Literal, Mapping, TypeAlias, Union

from inspect_ai import Epochs
from inspect_ai.approval import ApprovalPolicy
from inspect_ai.model import GenerateConfig
from inspect_ai.util import DisplayType, SandboxEnvironmentType
from pydantic import BaseModel, Field, field_validator

from inspect_flow._util.list_util import ensure_list_or_none

CreateArgs: TypeAlias = Mapping[str, Any]
ModelRolesConfig: TypeAlias = Mapping[str, Union["ModelConfig", str]]


class ModelConfig(BaseModel, extra="forbid"):
    """Configuration for a model."""

    name: str = Field(description="Name of the model to use.")

    role: str | None = Field(
        default=None,
        description="Optional named role for model (e.g. for roles specified at the task or eval level). Provide a default as a fallback in the case where the role hasn't been externally specified.",
    )

    default: str | None = Field(
        default=None,
        description="Optional. Fallback model in case the specified model or role is not found. Should be a fully qualified model name (e.g. openai/gpt-4o).",
    )

    # TODO:ransom should we disable extra?
    config: list[GenerateConfig] | None = Field(
        default=None,
        description="Configuration for model. If a list, will matrix over the values",
    )

    base_url: str | None = Field(
        default=None,
        description="Optional. Alternate base URL for model.",
    )

    api_key: None = Field(
        default=None,
        description="Hawk doesn't allow setting api_key because Hawk could accidentally log the API key.",
    )

    memoize: bool = Field(
        default=True,
        description="Use/store a cached version of the model based on the parameters to get_model().",
    )

    # Convert single items to lists
    @field_validator("config", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)


class Dependency(BaseModel, extra="forbid"):
    # TODO:ransom support requirements.txt/pyproj.toml for specifying dependencies
    package: str = Field(
        description="E.g. a PyPI package specifier or Git repository URL.",
    )


class SolverConfig(BaseModel, extra="forbid"):
    name: str = Field(description="Name of the solver.")

    args: list[CreateArgs] | None = Field(
        default=None,
        description="Solver arguments.",
    )

    # Convert single items to lists
    @field_validator("args", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)


class AgentConfig(BaseModel, extra="forbid"):
    name: str = Field(description="Name of the solver.")

    args: list[CreateArgs] | None = Field(
        default=None,
        description="Agent arguments.",
    )

    # Convert single items to lists
    @field_validator("args", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)


class TaskConfig(BaseModel, extra="forbid"):
    name: str = Field(description="Name of the task to use.")

    file: str | None = Field(
        default=None, description="Python file containing the task implementation"
    )

    args: list[CreateArgs] | None = Field(
        default=None,
        description="Task arguments",
    )

    models: list[ModelConfig] | None = Field(
        default=None,
        description="Model to use for evaluation. If not specified, the default model for the task will be used.",
    )

    model_roles: list[ModelRolesConfig] | None = Field(
        default=None,
        description="Model roles to use for evaluation.",
    )

    solvers: list[SolverConfig | list[SolverConfig] | AgentConfig] | None = Field(
        default=None,
        description="Solvers.",
    )

    # TODO:ransom sample_ids not implemented
    sample_id: str | int | list[str | int] | None = Field(
        default=None,
        min_length=1,
        description="Evaluate specific sample(s) from the dataset.",
    )

    epochs: int | Epochs | None = Field(
        default=None,
        description='Epochs to repeat samples for and optional score reducer function(s) used to combine sample scores (defaults to "mean")',
    )

    fail_on_error: bool | float | None = Field(
        default=None,
        description="`True` to fail on first sample error(default); `False` to never fail on sample errors; Value between 0 and 1 to fail if a proportion of total samples fails. Value greater than 1 to fail eval if a count of samples fails.",
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

    # Convert single items to lists
    @field_validator("args", "models", "model_roles", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)


class Matrix(BaseModel, extra="forbid"):
    tasks: list[TaskConfig] = Field(
        description="List of tasks to evaluate in this eval set."
    )

    args: list[CreateArgs] | None = Field(
        default=None,
        description="Task arguments or list of task arguments to use for evaluation.",
    )

    models: list[ModelConfig] | None = Field(
        default=None,
        description="Model or list of models to use for evaluation. If not specified, the default model for each task will be used.",
    )

    model_roles: list[ModelRolesConfig] | None = Field(
        default=None,
        description="Model roles to use for evaluation.",
    )

    solvers: list[SolverConfig | list[SolverConfig] | AgentConfig] | None = Field(
        default=None,
        description="Solvers.",
    )

    # Convert single items to lists
    @field_validator("tasks", "args", "models", "model_roles", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)


class FlowOptions(BaseModel, extra="forbid"):
    log_dir: str = Field(
        description="Output path for logging results (required to ensure that a unique storage scope is assigned for the set)."
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

    approval: str | list[ApprovalPolicy] | None = Field(
        default=None,
        description="Tool use approval policies.Either a path to an approval policy config file or a list of approval policies. Defaults to no approval policy.",
    )

    score: bool = Field(default=True, description="Score output (defaults to True)")

    log_level: str | None = Field(
        default=None,
        description='Level for logging to the console: "debug", "http", "sandbox", "info", "warning", "error", "critical", or "notset" (defaults to "warning")',
    )

    log_level_transcript: str | None = Field(
        default=None,
        description='Level for logging to the log file (defaults to "info")',
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

    debug_errors: bool | None = Field(
        default=None,
        description="Raise task errors (rather than logging them) so they can be debugged (defaults to False).",
    )

    max_samples: int | None = Field(
        default=None,
        description="Maximum number of samples to run in parallel (default is max_connections)",
    )

    max_tasks: int | None = Field(
        default=None,
        description="Maximum number of tasks to run in parallel(defaults to the greater of 4 and the number of models being evaluated)",
    )

    max_subprocesses: int | None = Field(
        default=None,
        description="Maximum number of subprocesses to run in parallel (default is os.cpu_count())",
    )

    max_sandboxes: int | None = Field(
        default=None,
        description="Maximum number of sandboxes (per-provider) to run in parallel.",
    )

    log_samples: bool | None = Field(
        default=None, description="Log detailed samples and scores (defaults to True)"
    )

    log_realtime: bool | None = Field(
        default=None,
        description="Log events in realtime (enables live viewing of samples in inspect view). Defaults to True.",
    )

    log_images: bool | None = Field(
        default=None,
        description="Log base64 encoded version of images, even if specified as a filename or URL (defaults to False)",
    )

    log_buffer: int | None = Field(
        default=None,
        description="Number of samples to buffer before writing log file. If not specified, an appropriate default for the format and filesystem is chosen (10 for most all cases, 100 for JSON logs on remote filesystems).",
    )

    log_shared: bool | None = Field(
        default=None,
        description="Sync sample events to log directory so that users on other systems can see log updates in realtime (defaults to no syncing). Specify `True` to sync every 10 seconds, otherwise an integer to sync every `n` seconds.",
    )

    log_dir_allow_dirty: bool | None = Field(
        default=None,
        description="If True, allow the log directory to contain unrelated logs. If False, ensure that the log directory only contains logs for tasks in this eval set (defaults to False).",
    )

    config: GenerateConfig | None = Field(
        default=None, description="Model generation options."
    )


class RetryOptions(BaseModel, extra="forbid"):
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

    retry_on_error: int | None = Field(
        default=None,
        description="Number of times to retry samples if they encounter errors (by default, no retries occur).",
    )


class SandboxOptions(BaseModel, extra="forbid"):
    sandbox: SandboxEnvironmentType | None = Field(
        default=None,
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec)",
    )

    sandbox_cleanup: bool | None = Field(
        default=None,
        description="Cleanup sandbox environments after task completes (defaults to True)",
    )


class FlowConfig(BaseModel, extra="forbid"):
    retry_options: RetryOptions | None = Field(
        default=None, description="Retry options"
    )
    sandbox_options: SandboxOptions | None = Field(
        default=None, description="Sandbox options"
    )
    options: FlowOptions | None = Field(default=None, description="Global options")
    dependencies: list[Dependency] | None = Field(
        default=None, description="Dependencies to pip install"
    )
    matrix: list[Matrix] = Field(description="Matrix of tasks to run")

    # Convert single items to lists
    @field_validator("dependencies", "matrix", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)
