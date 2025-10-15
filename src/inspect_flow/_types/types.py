from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypeVar,
    Union,
)

from inspect_ai.model import GenerateConfig
from pydantic import AfterValidator, BaseModel, Field, model_validator


class File(BaseModel):
    path: str = Field(description="Path to the file")


class EnvironmentConfig(BaseModel):
    pass


class TaskConfig(BaseModel):
    """Configuration for a task."""

    name: str = Field(description="Name of the task to use.")

    sample_ids: list[str | int] | None = Field(
        default=None,
        min_length=1,
        description="List of sample IDs to run for the task. If not specified, all samples will be run.",
    )


class GetModelArgs(BaseModel, extra="allow", serialize_by_alias=True):
    """Arguments to pass to Inspect's [get_model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) function."""

    role: str | None = Field(
        default=None,
        description="Optional named role for model (e.g. for roles specified at the task or eval level). Provide a default as a fallback in the case where the role hasn't been externally specified.",
    )

    default: str | None = Field(
        default=None,
        description="Optional. Fallback model in case the specified model or role is not found. Should be a fully qualified model name (e.g. openai/gpt-4o).",
    )

    # TODO:ransom should we disable extra?
    config: GenerateConfig | None = Field(
        default=None,
        alias="config",
        description="Configuration for model.",
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


class ModelConfig(BaseModel):
    """Configuration for a model."""

    name: str = Field(description="Name of the model to use.")

    args: GetModelArgs | None = Field(
        default=None,
        description="Arguments to pass to Inspect's [get_model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) function.",
    )


T = TypeVar("T", TaskConfig, ModelConfig)


def _validate_package(v: str) -> str:
    if not ("inspect-ai" in v or "inspect_ai" in v):
        return v

    error_message = (
        "It looks like you're trying to use tasks, solvers, or models from Inspect (e.g. built-in agents like "
        + "react and human_agent). To use these items, change the package field to the string 'inspect-ai'. "
        + "Remove any version specifier and don't try to specify a version of inspect-ai from GitHub."
    )
    try:
        import inspect_ai

        error_message += (
            f" hawk is using version {inspect_ai.__version__} of inspect-ai."
        )
    except ImportError:
        pass

    raise ValueError(error_message)


class PackageConfig(BaseModel, Generic[T]):
    """Configuration for a Python package that contains tasks, models, solvers, or agents."""

    package: Annotated[str, AfterValidator(_validate_package)] | None = Field(
        default=None,
        description="E.g. a PyPI package specifier or Git repository URL. To use items from the inspect-ai package, "
        + "use 'inspect-ai' (with a dash) as the package name. Do not include a version specifier or try to "
        + "install inspect-ai from GitHub.",
    )

    file: str | None = Field(default=None, description="file with task export")

    @model_validator(mode="after")
    def check_package_or_file(self):
        if (self.package is None) == (self.file is None):
            raise ValueError("Exactly one of package or file must be specified")
        return self

    name: str = Field(
        description="The package name. This must match the name of the package's setuptools entry point for inspect_ai. "
        + "The entry point must export the tasks, models, or solvers referenced in the `items` field."
    )

    items: list[T] = Field(
        description="List of tasks, models, or solvers to use from the package."
    )


class BuiltinConfig(BaseModel, Generic[T]):
    """Configuration for tasks, models, or solvers built into Inspect."""

    package: Literal["inspect-ai"] = Field(
        description="The name of the inspect-ai package."
    )

    items: list[T] = Field(
        description="List of tasks, models, or solvers to use from inspect-ai."
    )


class EvalSetConfig(BaseModel):
    tasks: list[PackageConfig[TaskConfig]] = Field(
        description="List of tasks to evaluate in this eval set."
    )

    log_dir: str = Field(description="Directory to write evaluation logs to.")

    models: list[PackageConfig[ModelConfig] | BuiltinConfig[ModelConfig]] | None = (
        Field(
            default=None,
            description="List of models to use for evaluation. If not specified, the default model for each task will be used.",
        )
    )

    limit: int | None = Field(
        default=None, description="Limit evaluated samples (defaults to all samples)."
    )


class TaskGroupConfig(BaseModel):
    eval_set: EvalSetConfig = Field(description="Evaluation set configuration")


class RunConfig(BaseModel):
    task_groups: list[TaskGroupConfig] = Field(
        default_factory=list, description="List of task group configurations"
    )


class Config(BaseModel):
    environment: EnvironmentConfig = Field(
        default_factory=EnvironmentConfig, description="Environment configuration"
    )
    run: RunConfig = Field(description="Run configuration")


# CONFIG PROPOSAL #2


class FlowOptions(BaseModel):
    log_dir: str = Field(description="Directory to write evaluation logs to.")
    limit: int | None = Field(
        default=None, description="Limit evaluated samples (defaults to all samples)."
    )


class Dependency(BaseModel):
    # TODO:ransom support requirements.txt/pyproj.toml for specifying dependencies
    package: Annotated[str, AfterValidator(_validate_package)] | None = Field(
        default=None,
        description="E.g. a PyPI package specifier or Git repository URL.",
    )

    file: str | None = Field(default=None, description="file with task export")

    @model_validator(mode="after")
    def check_package_or_file(self):
        if (self.package is None) == (self.file is None):
            raise ValueError("Exactly one of package or file must be specified")
        return self


class Task(BaseModel):
    name: str = Field(description="Name of the task to use.")

    sample_ids: list[str | int] | None = Field(
        default=None,
        min_length=1,
        description="List of sample IDs to run for the task. If not specified, all samples will be run.",
    )

    args: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description="Task arguments",
    )

    models: ModelConfig | list[ModelConfig] | None = Field(
        default=None,
        description="Model to use for evaluation. If not specified, the default model for the task will be used.",
    )


class Matrix(BaseModel):
    tasks: Task | list[Task] = Field(
        description="List of tasks to evaluate in this eval set."
    )

    args: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description="Task arguments or list of task arguments to use for evaluation.",
    )

    models: ModelConfig | list[ModelConfig] | None = Field(
        default=None,
        description="Model or list of models to use for evaluation. If not specified, the default model for each task will be used.",
    )


class FlowConfig(BaseModel):
    options: FlowOptions | None = Field(default=None, description="Global options")
    dependencies: Dependency | list[Dependency] | None = Field(
        default=None, description="Dependencies to pip install"
    )
    matrix: Matrix = Field(description="Matrix of tasks to run")
