# Type definitions for flow config files.
# Important: All default values should be None. This supports merging of partial configs as None values are not merged.
# But a different default value would override more specific settings.
from __future__ import annotations

import inspect
from dataclasses import fields as dataclass_fields
from typing import (
    Annotated,
    Any,
    Callable,
    Generic,
    Literal,
    Mapping,
    ParamSpec,
    Sequence,
    TypeAlias,
    TypeVar,
    overload,
)

import rich.repr
from inspect_ai import Task
from inspect_ai.agent import Agent
from inspect_ai.approval._policy import ApprovalPolicyConfig
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, Model, ModelCost
from inspect_ai.scorer import Scorer
from inspect_ai.solver import Solver
from inspect_ai.util import (
    CheckpointConfig,
    CheckpointTrigger,
    DisplayType,
    EarlyStopping,
    Manual,
    SandboxEnvironmentType,
    TimeInterval,
    TokenInterval,
    TokenLimit,
    TurnInterval,
)
from inspect_ai.util._checkpoint.config import CheckpointDisabled
from inspect_ai.util._checkpoint.parse_cli import (
    _CheckpointConfigModel,
    parse_checkpoint,
)
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    PlainSerializer,
    SkipValidation,
    model_validator,
)
from typing_extensions import Self, override

from inspect_flow._util.pydantic_util import model_dump

CreateArgs: TypeAlias = Mapping[str, Any]
LogFilter: TypeAlias = Callable[[EvalLog], bool]
"""A function that receives an `EvalLog` (header-only) and returns `True` to include the log or `False` to exclude it."""
ModelRolesConfig: TypeAlias = Mapping[str, "FlowModel | str | Model"]


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


def _validate_checkpoint(value: Any) -> Any:
    if isinstance(value, CheckpointDisabled):
        # normalize inspect's veto sentinel to `False`, which round-trips as a veto
        # (the sentinel's all-`None` fields would serialize to an enabling `{}`)
        return False
    if isinstance(value, (CheckpointConfig, bool)):
        return value
    if isinstance(value, str):
        return parse_checkpoint(value)
    if not isinstance(value, dict):
        raise ValueError(
            f"Invalid checkpoint value {value!r}: expected a CheckpointConfig, "
            "bool, string, or mapping"
        )
    # an explicit null means the same as an absent key: inherit
    value = {k: v for k, v in value.items() if v is not None}
    model = _CheckpointConfigModel.model_validate(
        {**value, "trigger": value.get("trigger", "manual")}
    )
    config = model.to_dataclass()
    # _CheckpointConfigModel targets whole-file configs and fills in defaults; flow
    # checkpoint dicts are partial layers where an absent field means "inherit".
    for field in dataclass_fields(config):
        if field.name not in value:
            setattr(config, field.name, None)
    return config


def _serialize_checkpoint_trigger(trigger: CheckpointTrigger) -> str | dict[str, Any]:
    match trigger:
        case Manual():
            return "manual"
        case TurnInterval(every=every):
            return {"type": "turn", "every": every}
        case TokenInterval(every=every):
            return {"type": "token", "every": every}
        case TimeInterval(every=every):
            # :f avoids scientific notation, which _parse_duration rejects
            return {"type": "time", "every": f"{every.total_seconds():f}s"}
        case _:
            raise ValueError(
                f"Checkpoint trigger {trigger!r} cannot be used in a serialized flow "
                "config; use a manual, turn, time, or token trigger."
            )


def _serialize_checkpoint(value: CheckpointConfig | bool) -> Any:
    if isinstance(value, bool):
        return value
    data: dict[str, Any] = {
        f.name: v
        for f in dataclass_fields(value)
        if f.name != "trigger" and (v := getattr(value, f.name)) is not None
    }
    if value.trigger is not None:
        data["trigger"] = _serialize_checkpoint_trigger(value.trigger)
    return data


FlowCheckpoint: TypeAlias = Annotated[
    SkipValidation[CheckpointConfig] | bool,
    BeforeValidator(
        _validate_checkpoint, json_schema_input_type=CheckpointConfig | bool | str
    ),
    PlainSerializer(_serialize_checkpoint),
]
"""`CheckpointConfig` with round-trippable (de)serialization.

`CheckpointConfig` cannot be validated directly: its trigger union members are
structurally identical dataclasses, so validating serialized data would lose the
trigger kind. Serialize triggers in inspect's discriminated `_CheckpointConfigModel`
form and validate through that model instead. Strings are parsed like the inspect
CLI's `--checkpoint` value (e.g. `"manual"`, `"turn:5"`, `"token:500k"`); `str`
appears only in the JSON schema (and generated dict types) — the validator converts
it, so the field never holds a string.
"""


class FlowBase(BaseModel, extra="forbid"):
    @override
    def __str__(self) -> str:
        return str(model_dump(self))

    def __rich_repr__(self) -> rich.repr.Result:
        for field in self.model_fields_set:
            if (value := getattr(self, field)) is not not_given:
                yield field, value


class FlowModel(FlowBase):
    """Configuration for a model.

    `name` is an Inspect model identifier (e.g. ``"openai/gpt-4o"``); `config`,
    `model_args`, `base_url`, `api_key`, and `role` tune how it is created.
    """

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the model to use. If factory is not provided, this is used to create the model.",
    )

    factory: FlowFactory[Model] | Callable[..., Model] | str | None | NotGiven = Field(
        default=not_given,
        description="Factory function to create the model instance.",
    )

    role: str | None | NotGiven = Field(
        default=not_given,
        description="Optional named role for model (e.g. for roles specified at the task or eval level). Provide a default as a fallback in the case where the role hasn't been externally specified.",
    )

    default: str | None | NotGiven = Field(
        default=not_given,
        description="Optional. Fallback model in case the specified model or role is not found. Should be a fully qualified model name (e.g. `openai/gpt-4o`).",
    )

    config: GenerateConfig | None | NotGiven = Field(
        default=not_given,
        description="Model generation config. Highest precedence: overrides `config` on `FlowTask` and `defaults.config`.",
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
        description="Use/store a cached version of the model based on the parameters to `get_model()`. Defaults to `True`.",
    )

    model_args: CreateArgs | None | NotGiven = Field(
        default=not_given, description="Additional args to pass to model constructor."
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the model.",
    )


class FlowScorer(FlowBase):
    """Configuration for a scorer: a registry `name` (or `factory`) plus its `args`."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the scorer. Used to create the scorer if the factory is not provided.",
    )

    factory: FlowFactory[Scorer] | Callable[..., Scorer] | str | None | NotGiven = (
        Field(
            default=not_given,
            description="Factory function to create the scorer instance.",
        )
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to scorer constructor.",
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the scorer.",
    )


class FlowSolver(FlowBase):
    """Configuration for a solver: a registry `name` (or `factory`) plus its `args`."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the solver. Used to create the solver if the factory is not provided.",
    )

    factory: FlowFactory[Solver] | Callable[..., Solver] | str | None | NotGiven = (
        Field(
            default=not_given,
            description="Factory function to create the solver instance.",
        )
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to solver constructor.",
    )

    flow_metadata: dict[str, Any] | None | NotGiven = Field(
        default=not_given,
        description="Optional. Metadata stored in the flow config. Not passed to the solver.",
    )


class FlowAgent(FlowBase):
    """Configuration for an agent: a registry `name` (or `factory`) plus its `args`."""

    name: str | None | NotGiven = Field(
        default=not_given,
        description="Name of the agent. Used to create the agent if the factory is not provided.",
    )

    factory: FlowFactory[Agent] | Callable[..., Agent] | str | None | NotGiven = Field(
        default=not_given,
        description="Factory function to create the agent instance.",
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


class FlowEpochs(FlowBase):
    """Configuration for task epochs.

    Number of epochs to repeat samples over and optionally one or more
    reducers used to combine scores from samples across epochs. If not
    specified the "mean" score reducer is used.
    """

    epochs: int = Field(description="Number of epochs.")

    reducer: str | Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description='One or more reducers used to combine scores from samples across epochs (defaults to `"mean"`)',
    )


class FlowExtraArgs(FlowBase):
    """Extra args to provide to the creation of Inspect objects."""

    model: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Extra args to pass to model constructor.",
    )
    solver: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Extra args to pass to solver constructor.",
    )
    agent: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Extra args to pass to agent constructor.",
    )
    scorer: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Extra args to pass to scorer constructor.",
    )


P = ParamSpec("P")
R = TypeVar("R", bound=Task | Agent | Solver | Scorer | Model)


class FlowFactory(BaseModel, Generic[R], arbitrary_types_allowed=True):
    """Type-checked factory wrapper for creating Inspect AI objects.

    Wraps a factory callable or string reference with its arguments. When a
    callable is provided, arguments are bound at construction time so that type
    errors are caught immediately rather than at evaluation time. When a string
    is provided, it is treated as a registry name (equivalent to passing a string
    directly to the ``factory`` field of the parent Flow type).

    Works with `FlowTask`, `FlowAgent`, `FlowSolver`, `FlowScorer`, and `FlowModel`.

    Positional and keyword arguments passed to the factory at construction are
    collected into the `args` field and forwarded to the factory at evaluation
    time.

    Attributes:
        factory: Factory function (e.g. a `@task`-decorated function) or string
            registry name.
        *args: Positional arguments forwarded to the factory (callable only).
        **kwargs: Keyword arguments forwarded to the factory.
    """

    factory: Callable[..., R] | str
    args: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="wrap")
    @classmethod
    def _validate(cls, value: Any, handler: Any) -> Any:
        # Use the base class (not cls) since Pydantic creates concrete subclasses for
        # each generic specialization (e.g. FlowFactory[Agent]), and an unspecialized
        # FlowFactory instance would fail isinstance(value, cls) for those subclasses.
        if isinstance(value, FlowFactory):
            return value
        # Reject dicts that don't look like FlowFactory field data so that Pydantic's
        # union validation can fall through to the next candidate (e.g. NotGiven).
        if not isinstance(value, dict) or "factory" not in value:
            raise ValueError("Expected a FlowFactory instance or dict with 'factory'")
        return handler(value)

    @overload
    def __init__(self, factory: str, **kw_args: Any) -> None: ...

    @overload
    def __init__(
        self, factory: Callable[P, R], *pos_args: P.args, **kw_args: P.kwargs
    ) -> None: ...

    def __init__(
        self,
        factory: Callable[P, R] | str,
        *pos_args: P.args,
        **kw_args: P.kwargs,
    ) -> None:
        if not pos_args and set(kw_args.keys()) <= {"args"}:
            # Pydantic calls __init__ with field data during validation. Set fields
            # directly to break the cycle — calling super().__init__() would recurse.
            object.__setattr__(
                self, "__dict__", {"factory": factory, "args": kw_args.get("args", {})}
            )
            object.__setattr__(self, "__pydantic_fields_set__", {"factory", "args"})
            object.__setattr__(self, "__pydantic_extra__", None)
        elif isinstance(factory, str):
            super().__init__(factory=factory, args=kw_args)
        else:
            sig = inspect.signature(factory)
            bound = sig.bind(*pos_args, **kw_args)
            super().__init__(factory=factory, args=dict(bound.arguments))

    def instantiate(self) -> R:
        assert callable(self.factory)
        return self.factory(**self.args)


class FlowTask(FlowBase, arbitrary_types_allowed=True):
    """Configuration for a single evaluation task.

    Identifies the task (`name` or `factory`) and carries its per-task settings:
    `model`, `solver`, `scorer`, `config` (generation config), `epochs`, `sandbox`,
    `approval`, and the various limits. Unset fields fall back to `FlowDefaults`.
    """

    name: str | None | NotGiven = Field(
        default=not_given,
        description='Task name. Any of registry name (`"inspect_evals/mbpp"`), file name (`"./my_task.py"`), or a file name and attr (`"./my_task.py@task_name"`). Used to create the task if the factory is not provided.',
    )

    factory: FlowFactory[Task] | Callable[..., Task] | str | None | NotGiven = Field(
        default=not_given,
        description="Factory function to create the task instance.",
    )

    args: CreateArgs | None | NotGiven = Field(
        default=not_given,
        description="Additional args to pass to task constructor",
    )

    extra_args: FlowExtraArgs | None | NotGiven = Field(
        default=not_given,
        description="Extra args to provide to creation of inspect objects for this task. Will override args provided in the `args` field on the `FlowModel`, `FlowSolver`, `FlowScorer`, and `FlowAgent`.",
    )

    solver: (
        str
        | FlowSolver
        | FlowAgent
        | Solver
        | Agent
        | Sequence[str | FlowSolver | Solver]
        | None
        | NotGiven
    ) = Field(
        default=not_given,
        description="Solver or list of solvers. Defaults to `generate()`, a normal call to the model.",
    )

    scorer: (
        str
        | FlowScorer
        | Scorer
        | Sequence[str | FlowScorer | Scorer]
        | None
        | NotGiven
    ) = Field(
        default=not_given,
        description="Scorer or list of scorers used to evaluate model output.",
    )

    model: str | FlowModel | Model | None | NotGiven = Field(
        default=not_given,
        description="Default model for task (Optional, defaults to eval model).",
    )

    config: GenerateConfig | NotGiven = Field(
        default=not_given,
        description="Model generation config for the default model (does not apply to model roles). Overrides `defaults.config`; overridden by `FlowModel.config`.",
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
        description='Epochs to repeat samples for and optional score reducer function(s) used to combine sample scores (defaults to `"mean"`)',
    )

    fail_on_error: bool | float | None | NotGiven = Field(
        default=not_given,
        description="`True` to fail on first sample error (default); `False` to never fail on sample errors; Value between 0 and 1 to fail if a proportion of total samples fails. Value greater than 1 to fail eval if a count of samples fails.",
    )

    continue_on_fail: bool | None | NotGiven = Field(
        default=not_given,
        description="`True` to continue running and only fail at the end if the `fail_on_error` condition is met. `False` to fail eval immediately when the `fail_on_error` condition is met (default).",
    )

    score_on_error: bool | None | NotGiven = Field(
        default=not_given,
        description="Score samples that error rather than failing the eval mid-run. Overridden by `options.score_on_error` when set.",
    )

    checkpoint: FlowCheckpoint | None | NotGiven = Field(
        default=not_given,
        description="Checkpoint configuration for this task, or `True` to enable checkpointing with the default trigger (every 500k tokens). Merged per-field with `options.checkpoint`, which takes precedence; `False` at either level disables checkpointing.",
    )

    message_limit: int | None | NotGiven = Field(
        default=not_given, description="Limit on total messages used for each sample."
    )

    token_limit: int | str | TokenLimit | None | NotGiven = Field(
        default=not_given,
        description="Limit on total tokens used for each sample. May be an integer, a string with a unit suffix (e.g. `'1M'`), or a `TokenLimit`.",
    )

    turn_limit: int | None | NotGiven = Field(
        default=not_given,
        description="Limit on total turns (assistant messages) for each sample.",
    )

    time_limit: int | None | NotGiven = Field(
        default=not_given, description="Limit on clock time (in seconds) for samples."
    )

    working_limit: int | None | NotGiven = Field(
        default=not_given,
        description="Limit on working time (in seconds) for sample. Working time includes model generation, tool calls, etc. but does not include time spent waiting on retries or shared resources.",
    )

    cost_limit: float | None | NotGiven = Field(
        default=not_given,
        description="Limit on total cost (in dollars) for each sample. Requires model cost data via model_cost_config.",
    )

    early_stopping: SkipValidation[EarlyStopping] | None | NotGiven = Field(
        default=not_given,
        description="Early stopping callbacks.",
    )

    version: int | str | NotGiven = Field(
        default=not_given,
        description="Expected version of the task. Verified against the version of the loaded task; instantiation fails if they do not match.",
    )

    tags: Sequence[str] | None | NotGiven = Field(
        default=not_given, description="Tags to associate with the task."
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


class FlowOptions(FlowBase):
    """Eval-set-wide options forwarded to Inspect's ``eval_set``.

    These apply to the whole run (retries, sandbox cleanup, global limits, display,
    scoring, the control channel, etc.) rather than to individual tasks — set per-task
    settings on `FlowTask`. Attached to a spec via ``FlowSpec(options=...)``.
    """

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
        description="Reduce `max_connections` at this rate with each retry (defaults to 1.0, which results in no reduction).",
    )

    retry_cleanup: bool | None | NotGiven = Field(
        default=not_given,
        description="Cleanup failed log files after retries (defaults to `True`).",
    )

    sandbox: SandboxEnvironmentType | None | NotGiven = Field(
        default=not_given,
        description="Sandbox environment type (or optionally a str or tuple with a shorthand spec).",
    )

    sandbox_cleanup: bool | None | NotGiven = Field(
        default=not_given,
        description="Cleanup sandbox environments after task completes (defaults to `True`).",
    )

    checkpoint: FlowCheckpoint | None | NotGiven = Field(
        default=not_given,
        description="Checkpoint configuration for this eval set, or `True` to enable checkpointing with the default trigger (every 500k tokens). Merged per-field with task- and sample-level `checkpoint`, taking precedence over both; `False` here or on a task disables checkpointing.",
    )

    acp_server: bool | int | str | None | NotGiven = Field(
        default=not_given,
        description="Override the original eval's ACP server transport on retry. `True` enables a default AF_UNIX socket; an integer binds a TCP loopback port; a string is taken as a custom UNIX socket path; `None` (default) replays whatever transport (or no transport) was persisted in the original log's `EvalConfig.acp_server`.",
    )

    ctl_server: bool | str | None | NotGiven = Field(
        default=not_given,
        description='Control-channel server for this eval-set process. `True` or `None` (default) binds the default AF_UNIX socket; `False` disables the control endpoint; `"keep-alive"` additionally keeps the process running after the eval-set finishes so external clients (the `inspect ctl` CLI, scripted agents, TUIs) can still query state and read results — exit via `inspect ctl release` (or `POST /release`). Requires `retry_immediate=True` (the default) for the `"keep-alive"` value.',
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
        default=not_given, description="Task display type (defaults to `'rich'`)."
    )

    approval: str | ApprovalPolicyConfig | None | NotGiven = Field(
        default=not_given,
        description="Tool use approval policies. Either a path to an approval policy config file or a list of approval policies. Defaults to no approval policy.",
    )

    score: bool | None | NotGiven = Field(
        default=not_given, description="Score output (defaults to `True`)."
    )

    score_display: bool | None | NotGiven = Field(
        default=not_given,
        description="Show scoring metrics in realtime (defaults to `True`).",
    )

    notification: bool | str | None | NotGiven = Field(
        default=not_given,
        description="Enable out-of-band notifications when a human-in-the-loop interaction (`ask_user`, human approval) is posted. Pass `True` to send via the URL(s) in the `INSPECT_EVAL_NOTIFICATION` environment variable (single URL, comma-separated list, or path to an Apprise config file). Alternatively pass a path to an Apprise YAML/text config file. URLs are not accepted directly so secrets never end up in source code, shell history, process listings, or eval logs. Requires the `apprise` package.",
    )

    log_level: str | None | NotGiven = Field(
        default=not_given,
        description='Level for logging to the console: `"debug"`, `"http"`, `"sandbox"`, `"info"`, `"warning"`, `"error"`, `"critical"`, or `"notset"` (defaults to `"warning"`).',
    )

    log_level_transcript: str | None | NotGiven = Field(
        default=not_given,
        description='Level for logging to the log file (defaults to `"info"`).',
    )

    log_format: Literal["eval", "json"] | None | NotGiven = Field(
        default=not_given,
        description='Format for writing log files (defaults to `"eval"`, the native high-performance format).',
    )

    limit: int | tuple[int, int] | None | NotGiven = Field(
        default=not_given,
        description="Limit evaluated samples: an integer for the first `n` samples, or a `(start, end)` tuple for a range (defaults to all samples).",
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

    score_on_error: bool | None | NotGiven = Field(
        default=not_given,
        description="Score samples that error rather than failing the eval mid-run. Errors still count toward the `fail_on_error` threshold for marking the eval log as 'error'. Only takes effect after retries (if any) are exhausted.",
    )

    debug_errors: bool | None | NotGiven = Field(
        default=not_given,
        description="Raise task errors (rather than logging them) so they can be debugged (defaults to `False`).",
    )

    model_cost_config: str | dict[str, ModelCost] | None | NotGiven = Field(
        default=not_given,
        description="YAML or JSON file with model prices for cost tracking.",
    )

    max_samples: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of samples to run in parallel (default is `max_connections`).",
    )

    max_dataset_memory: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum MB of dataset sample data to hold in memory per task. When exceeded, samples are paged to a temporary file on disk (defaults to `None`, which keeps all samples in memory).",
    )

    max_tasks: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of tasks to run in parallel (defaults is 10).",
    )

    max_subprocesses: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of subprocesses to run in parallel (default is `os.cpu_count()`).",
    )

    max_sandboxes: int | None | NotGiven = Field(
        default=not_given,
        description="Maximum number of sandboxes (per-provider) to run in parallel.",
    )

    log_samples: bool | None | NotGiven = Field(
        default=not_given,
        description="Log detailed samples and scores (defaults to `True`).",
    )

    log_realtime: bool | None | NotGiven = Field(
        default=not_given,
        description="Log events in realtime (enables live viewing of samples in inspect view) (defaults to `True`).",
    )

    log_images: bool | None | NotGiven = Field(
        default=not_given,
        description="Log base64 encoded version of images, even if specified as a filename or URL (defaults to `False`).",
    )

    log_model_api: bool | None | NotGiven = Field(
        default=not_given,
        description="Log raw model api requests and responses. Note that error requests/responses are always logged.",
    )

    log_refusals: bool | None | NotGiven = Field(
        default=not_given,
        description="Log warnings for model refusals.",
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
        description="If specified, the log viewer and logs generated by this eval set will be bundled into this directory. Relative paths will be resolved relative to the config file (when using the CLI) or `base_dir` arg (when using the API).",
    )

    bundle_overwrite: bool | None | NotGiven = Field(
        default=not_given,
        description="Whether to overwrite files in the `bundle_dir` (defaults to `False`).",
    )

    log_dir_allow_dirty: bool | None | NotGiven = Field(
        default=not_given,
        description="If `True`, allow the log directory to contain unrelated logs. If `False`, ensure that the log directory only contains logs for tasks in this eval set (defaults to `False`).",
    )

    eval_set_id: str | None | NotGiven = Field(
        default=not_given,
        description="ID for the eval set. If not specified, a unique ID will be generated.",
    )

    embed_viewer: bool | None | NotGiven = Field(
        default=not_given,
        description="If True, embed a log viewer into the log directory.",
    )

    bundle_url_mappings: dict[str, str] | None | NotGiven = Field(
        default=not_given,
        description="Replacements applied to `bundle_dir` to generate a URL. If provided and `bundle_dir` is set, the mapped URL will be written to stdout.",
    )


class FlowDefaults(FlowBase):
    """Default `model`/`solver`/`agent`/`task` values applied to every task in the spec.

    A value set on an individual `FlowTask` overrides the default here. The ``*_prefix``
    variants apply defaults by registry-name prefix. Attached via ``FlowSpec(defaults=...)``.
    """

    config: GenerateConfig | None | NotGiven = Field(
        default=not_given,
        description="Default model generation config. Lowest precedence: overridden by `config` on `FlowTask` and `FlowModel`.",
    )

    agent: FlowAgent | None | NotGiven = Field(
        default=not_given, description="Field defaults for agents."
    )

    agent_prefix: dict[str, FlowAgent] | None | NotGiven = Field(
        default=not_given,
        description="Agent defaults for agent name prefixes. E.g. `{'inspect/': FAgent(...)}`",
    )

    model: FlowModel | None | NotGiven = Field(
        default=not_given, description="Field defaults for models."
    )

    model_prefix: dict[str, FlowModel] | None | NotGiven = Field(
        default=not_given,
        description="Model defaults for model name prefixes. E.g. `{'openai/': FModel(...)}`",
    )

    solver: FlowSolver | None | NotGiven = Field(
        default=not_given, description="Field defaults for solvers."
    )

    solver_prefix: dict[str, FlowSolver] | None | NotGiven = Field(
        default=not_given,
        description="Solver defaults for solver name prefixes. E.g. `{'inspect/': FSolver(...)}`",
    )

    task: FlowTask | None | NotGiven = Field(
        default=not_given, description="Field defaults for tasks."
    )

    task_prefix: dict[str, FlowTask] | None | NotGiven = Field(
        default=not_given,
        description="Task defaults for task name prefixes. E.g. `{'inspect_evals/': FTask(...)}`",
    )


class FlowDependencies(FlowBase):
    """Dependencies to install in the per-run virtual environment.

    Only applies in venv execution mode (``execution_type="venv"``); combines an optional
    `dependency_file`, `additional_dependencies`, and automatic detection
    (`auto_detect_dependencies`).
    """

    dependency_file: Literal["auto", "no_file"] | str | None | NotGiven = Field(
        default=not_given,
        description="Path to a dependency file (either `requirements.txt` or `pyproject.toml`) to use to create the virtual environment. If `'auto'`, will search the path starting from the same directory as the config file (when using the CLI) or `base_dir` arg (when using the API) looking for `pyproject.toml` or `requirements.txt` files. If `'no_file'`, no dependency file will be used. Defaults to `'auto'`.",
    )

    additional_dependencies: str | Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description="Dependencies to pip install. E.g. PyPI package specifiers or Git repository URLs.",
    )

    auto_detect_dependencies: bool | None | NotGiven = Field(
        default=not_given,
        description="If `True`, automatically detect and install dependencies from names of objects in the config (defaults to `True`). For example, if a model name starts with `'openai/'`, the `'openai'` package will be installed. If a task name is `'inspect_evals/mmlu'` then the `'inspect-evals'` package will be installed.",
    )

    uv_sync_args: str | Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description="Additional arguments to pass to `uv sync` when creating the virtual environment using a `pyproject.toml` file. May be a string (`'--dev --extra test'`) or a list of strings (`['--dev', '--extra', 'test']`).",
    )


InstantiateMode: TypeAlias = Literal["serial", "by_task", "parallel"]


class InstantiateConfig(FlowBase):
    """Configuration for task instantiation parallelism."""

    mode: InstantiateMode = Field(
        default="serial",
        description="`'serial'` instantiates one task at a time. `'by_task'` parallelizes across distinct task names but serializes instances that share a name. `'parallel'` instantiates everything concurrently.",
    )

    max_threads: int = Field(
        default=32,
        description="Maximum worker threads to use for instantiation.",
    )


class FlowInternal(FlowBase):
    """State populated by the spec loader. Not intended for direct user configuration.

    Carries information from the parent process to the venv subprocess that is
    not part of the user-facing spec.
    """

    preload_files: Sequence[str] | None | NotGiven = Field(
        default=not_given,
        description=(
            "Absolute paths to Python files the runner should execute for "
            "their side effects (e.g. registering decorators) before task "
            "instantiation. Populated automatically by the spec loader from "
            "any files that register `@after_instantiate` (or similar "
            "runner-side decorators) at load time."
        ),
    )


class FlowStoreConfig(FlowBase):
    """Store configuration with optional log filter."""

    path: Literal["auto"] | str | None = Field(
        default="auto",
        description="Path to directory to use for flow storage. `'auto'` will use a default application location. `None` will disable storage.",
    )

    filter: (
        SkipValidation[LogFilter]
        | str
        | Sequence[SkipValidation[LogFilter] | str]
        | None
    ) = Field(
        default=None,
        description="Log filter to apply when searching for existing logs. Can be a callable, a registered filter name, a sequence of filters (all must pass), or `None`.",
    )

    read: bool = Field(
        default=False,
        description="Whether to match existing logs from the store. Default is `False`.",
    )

    write: bool = Field(
        default=True,
        description="Whether to index completed logs in the store. Default is `True`.",
    )


class FlowSpec(FlowBase, arbitrary_types_allowed=True):
    """Top-level flow specification: the tasks to run plus how to run them.

    This is the root object of every flow config. Settings are grouped by scope, and
    putting each in the right place avoids the most common configuration mistake:

    - **What to evaluate** — `tasks`, a list of `FlowTask`. Per-task settings (`model`,
      `solver`, `scorer`, `config`, `epochs`, limits) live on each `FlowTask`, not here.
    - **Defaults across tasks** — `defaults` (`FlowDefaults`), applied to every task. A
      value set on an individual `FlowTask` overrides the matching default.
    - **Eval-set-wide options** — `options` (`FlowOptions`), forwarded to Inspect's
      `eval_set()`. These apply to the whole run (retries, global limits, display,
      scoring), not to individual tasks.
    - **Run environment** — top-level fields on this spec: `execution_type`,
      `python_version`, `dependencies` (venv mode), `env`, `store`, `log_dir`.

    Model generation `config` can be set in several places; later entries win:
    `defaults.config` < `FlowTask.config` < `FlowModel.config`.

    Eval parameters (`model`, `solver`, limits, etc.) are not set directly on `FlowSpec`;
    put them on `FlowTask` (or `defaults` to apply them to every task).
    """

    includes: Sequence[str | FlowSpec] | None | NotGiven = Field(
        default=not_given,
        description="List of other flow specs to include. Relative paths will be resolved relative to the config file (when using the CLI) or `base_dir` arg (when using the API). In addition to this list of explicit files to include, any `_flow.py` files in the same directory or any parent directory of the config file (when using the CLI) or `base_dir` arg (when using the API) will also be included automatically.",
    )

    store: Literal["auto"] | str | FlowStoreConfig | None | NotGiven = Field(
        default=not_given,
        description="Path to directory to use for flow storage, or a `FlowStoreConfig` with path and filter options. `'auto'` will use a default application location. `None` will disable storage. Relative paths will be resolved relative to the config file (when using the CLI) or `base_dir` arg (when using the API). If not given, `'auto'` will be used.",
    )

    log_dir: str | None | NotGiven = Field(
        default=not_given,
        description="Output path for logging results (required to ensure that a unique storage scope is assigned). Must be set before running the flow spec. Relative paths will be resolved relative to the config file (when using the CLI) or `base_dir` arg (when using the API).",
    )

    log_dir_create_unique: bool | None | NotGiven = Field(
        default=not_given,
        description="If `True`, create a unique log directory by appending a datetime subdirectory (e.g. `2025-12-09T17-36-43`) under the specified `log_dir`. If `False`, use the existing `log_dir` (which must be empty or have `log_dir_allow_dirty=True`). Defaults to `False`.",
    )

    execution_type: Literal["inproc", "venv"] | None | NotGiven = Field(
        default=not_given,
        description="Execution environment for running tasks (defaults to `'inproc'`).",
    )

    python_version: str | None | NotGiven = Field(
        default=not_given,
        description="Python version to use in the flow virtual environment (e.g. `'3.11'`).",
    )

    dependencies: FlowDependencies | None | NotGiven = Field(
        default=not_given,
        description="Dependencies to install in the venv. Defaults to auto-detecting dependencies from `pyproject.toml`, `requirements.txt`, and object names in the config.",
    )

    options: FlowOptions | None | NotGiven = Field(
        default=not_given, description="Arguments for calls to `eval_set()`."
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

    tasks: Sequence[str | FlowTask | Task] | None | NotGiven = Field(
        default=not_given, description="Tasks to run"
    )

    instantiate: InstantiateMode | InstantiateConfig | None | NotGiven = Field(
        default=not_given,
        description="How to instantiate tasks before running. `'serial'` (default) instantiates one task at a time. `'by_task'` parallelizes across distinct task names but serializes instances that share a name. `'parallel'` instantiates everything concurrently. Pass an `InstantiateConfig` to also set `max_threads`.",
    )

    internal: FlowInternal | None | NotGiven = Field(
        default=not_given,
        description="Internal state populated by the spec loader. Not intended for direct user configuration.",
    )
