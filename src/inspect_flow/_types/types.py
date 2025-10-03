from pydantic import BaseModel, Field


class File(BaseModel):
    path: str = Field(description="Path to the file")


class EnvironmentConfig(BaseModel):
    pass


class EvalSetConfig(BaseModel):
    pass


class TaskGroupConfig(BaseModel):
    uv_lock_file: File = Field(description="uv.lock file")
    eval_set: EvalSetConfig = Field(description="Evaluation set configuration")


class RunConfig(BaseModel):
    task_groups: list[TaskGroupConfig] = Field(
        default_factory=list, description="List of task group configurations"
    )


class Config(BaseModel):
    environment: EnvironmentConfig = Field(description="Environment configuration")
    run: RunConfig = Field(description="Run configuration")
