from typing import Any, Mapping, TypeAlias, Union

from inspect_ai.model import GenerateConfig
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


class FlowOptions(BaseModel, extra="forbid"):
    log_dir: str = Field(description="Directory to write evaluation logs to.")
    limit: int | None = Field(
        default=None, description="Limit evaluated samples (defaults to all samples)."
    )


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

    # TODO:ransom sample_ids not implemented
    sample_ids: list[str | int] | None = Field(
        default=None,
        min_length=1,
        description="List of sample IDs to run for the task. If not specified, all samples will be run.",
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


class FlowConfig(BaseModel, extra="forbid"):
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
