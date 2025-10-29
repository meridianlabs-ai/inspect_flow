from typing import (
    Any,
    Literal,
    Mapping,
    TypeAlias,
    TypeVar,
    Union,
    overload,
)

from inspect_ai.approval._policy import (
    ApprovalPolicyConfig,
)  # TODO:ransom private import
from inspect_ai.model import GenerateConfig
from inspect_ai.util import (
    DisplayType,
    SandboxEnvironmentType,
)
from pydantic import BaseModel, Field, field_validator, model_validator

from inspect_flow._util.list_util import ensure_list_or_none

CreateArgs: TypeAlias = Mapping[str, Any]
ModelRolesConfig: TypeAlias = Mapping[str, Union["FlowModel", str]]


class FlowModel(BaseModel, extra="forbid"):
    name: str = Field(description="Name of the model to use.")

    role: str | None = Field(
        default=None,
        description="Optional named role for model (e.g. for roles specified at the task or eval level). Provide a default as a fallback in the case where the role hasn't been externally specified.",
    )

    default: str | None = Field(
        default=None,
        description="Optional. Fallback model in case the specified model or role is not found. Should be a fully qualified model name (e.g. openai/gpt-4o).",
    )

    # TODO:ransom should we forbid extra on GenerateConfig?
    config: GenerateConfig | None = Field(
        default=None,
        description="Configuration for model. Config values will be override settings on the FlowTask and FlowConfig.",
    )

    base_url: str | None = Field(
        default=None,
        description="Optional. Alternate base URL for model.",
    )

    api_key: str | None = Field(
        default=None,
        description="Optional. API key for model.",
    )

    memoize: bool = Field(
        default=True,
        description="Use/store a cached version of the model based on the parameters to get_model().",
    )

    model_args: CreateArgs | None = Field(
        default=None, description="Additional args to pass to model constructor."
    )


class FlowSolver(BaseModel, extra="forbid"):
    name: str = Field(description="Name of the solver.")

    args: CreateArgs | None = Field(
        default=None,
        description="Additional args to pass to solver constructor.",
    )


class FlowAgent(BaseModel, extra="forbid"):
    name: str = Field(description="Name of the solver.")

    args: CreateArgs | None = Field(
        default=None,
        description="Additional args to pass to agent constructor.",
    )


class FlowEpochs(BaseModel):
    epochs: int = Field(description="Number of epochs.")

    reducer: str | list[str] | None = Field(
        default=None,
        description='One or more reducers used to combine scores from samples across epochs (defaults to "mean")',
    )


class FlowTask(BaseModel, extra="forbid"):
    name: str | None = Field(
        default=None,
        description='Task name. If not specified is automatically determined based on the name of the task directory (or "task") if its anonymous task (e.g. created by a function exported from a file.',
    )

    file: str | None = Field(
        default=None,
        description="Python file containing the task implementation. If not provided, the task will be loaded from the registry.",
    )

    file_attr: str | None = Field(
        default=None,
        description="Name of the task factory attr within file. Only used if file is specified. Defaults to 'name'.",
    )

    registry_name: str | None = Field(
        default=None,
        description="Name of the task within the registry. Only used if file is not specified. Defaults to 'name'.",
    )

    args: CreateArgs | None = Field(
        default=None,
        description="Additional args to pass to task constructor",
    )

    solver: FlowSolver | list[FlowSolver] | FlowAgent | None = Field(
        default=None,
        description="Solver or list of solvers. Defaults to generate(), a normal call to the model.",
    )

    model: FlowModel | None = Field(
        default=None,
        description="Default model for task (Optional, defaults to eval model).",
    )

    config: GenerateConfig | None = Field(
        default=None,
        description="Model generation config for default model (does not apply to model roles). Will override config settings on the FlowConfig. Will be overridden by settings on the FlowModel.",
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

    version: int | None = Field(
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

    @field_validator("model", mode="before")
    @classmethod
    def convert_string_model(cls, v):
        return convert_str_to_class(FlowModel, v)

    @field_validator("solver", mode="before")
    @classmethod
    def convert_string_solvers(cls, v):
        return convert_str_to_solver(v)

    @model_validator(mode="after")
    def validate_field_combinations(self):
        if self.file is not None:
            if self.registry_name is not None:
                raise ValueError(
                    "registry_name cannot be specified when file is specified"
                )
        elif self.file_attr is not None:
            raise ValueError("file_attr cannot be specified when file is not specified")
        elif self.registry_name is None and self.name is None:
            raise ValueError(
                "FlowTask must have at least one of registry_name, name, or file specified"
            )

        return self


class FlowOptions(BaseModel, extra="forbid"):
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
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec)",
    )

    sandbox_cleanup: bool | None = Field(
        default=None,
        description="Cleanup sandbox environments after task completes (defaults to True)",
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
        description="Number of times to retry samples if they encounter errors (by default, no retries occur).",
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

    log_shared: bool | int | None = Field(
        default=None,
        description="Sync sample events to log directory so that users on other systems can see log updates in realtime (defaults to no syncing). Specify `True` to sync every 10 seconds, otherwise an integer to sync every `n` seconds.",
    )

    log_dir_allow_dirty: bool | None = Field(
        default=None,
        description="If True, allow the log directory to contain unrelated logs. If False, ensure that the log directory only contains logs for tasks in this eval set (defaults to False).",
    )


class FlowConfig(BaseModel, extra="forbid"):
    flow_dir: str = Field(
        default="logs/flow",
        description="Output path for flow data and logging results (required to ensure that a unique storage scope is assigned).",
    )

    python_version: str | None = Field(
        default=None,
        description="Python version to use in the flow virtual environment (e.g. '3.11')",
    )

    options: FlowOptions | None = Field(
        default=None, description="Arguments for calls to eval_set."
    )

    config: GenerateConfig | None = Field(
        default=None,
        description="Default model generation options. Will be overriden by settings on the FlowModel and FlowTask.",
    )

    dependencies: list[str] | None = Field(
        # TODO:ransom support requirements.txt/pyproj.toml for specifying dependencies
        default=None,
        description="Dependencies to pip install. E.g. PyPI package specifiers or Git repository URLs.",
    )

    tasks: list[FlowTask] = Field(description="Tasks to run")

    # Convert single items to lists
    @field_validator("dependencies", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return ensure_list_or_none(v)

    @field_validator("tasks", mode="before")
    @classmethod
    def convert_string_tasks(cls, v):
        return convert_to_task_list(v)


def convert_to_task_list(
    v: str | FlowTask | list[str | FlowTask] | None,
) -> list[FlowTask] | None:
    if v is None:
        return v
    if not isinstance(v, list):
        v = [v]
    return [FlowTask(name=task) if isinstance(task, str) else task for task in v]


T = TypeVar("T", FlowModel, FlowSolver)


@overload
def convert_str_to_class(cls: type[T], v: None) -> None: ...


@overload
def convert_str_to_class(cls: type[T], v: str | T) -> T: ...


def convert_str_to_class(cls: type[T], v: str | T | None) -> T | None:
    return cls(name=v) if isinstance(v, str) else v


def convert_str_to_solver(
    v: str | FlowSolver | list[str | FlowSolver] | None,
) -> FlowSolver | list[FlowSolver] | None:
    if v is None:
        return None
    if isinstance(v, list):
        return [convert_str_to_class(FlowSolver, solver) for solver in v]
    return convert_str_to_class(FlowSolver, v)
