from typing import Literal

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import Model, get_model


@task
def noop() -> Task:
    return Task(
        dataset=[
            Sample(id=1, input="Test sample 1"),
            Sample(id=2, input="Test sample 2"),
        ]
    )


@task
def noop2() -> Task:
    return Task()


@task
def task_with_get_model() -> Task:
    _model = get_model()
    return Task()


@task
def task_with_params(
    subset: Literal["original", "contrast"] = "original",
    use_system_prompt: bool = False,
    grader: list[str | Model | None] | str | Model | None = "openai/gpt-3.5-turbo",
) -> Task:
    task = Task(
        metadata={
            "subset": subset,
            "use_system_prompt": use_system_prompt,
            "grader": grader,
        }
    )
    return task


@task
def task_with_model_roles() -> Task:
    _model1 = get_model(role="mark")
    _model2 = get_model(role="conartist")
    return Task()
