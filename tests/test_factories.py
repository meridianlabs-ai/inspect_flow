import pytest
from inspect_flow import configs_matrix, tasks_matrix, tasks_with
from inspect_flow.types import FlowModel, FlowTask
from pydantic import ValidationError

from tests.test_helpers.type_helpers import ft


def test_tasks_x_models():
    result = tasks_matrix(task=["task1", "task2"], model=["model1", "model2"])
    result = [ft(r) for r in result]
    assert len(result) == 4
    assert result[0].name == "task1"
    assert result[0].model
    assert result[0].model.name == "model1"
    assert result[1].name == "task1"
    assert result[1].model
    assert result[1].model.name == "model2"
    assert result[2].name == "task2"
    assert result[2].model
    assert result[2].model.name == "model1"
    assert result[3].name == "task2"
    assert result[3].model
    assert result[3].model.name == "model2"


def test_flow_task_x_models():
    result = tasks_matrix(task=FlowTask(name="task1"), model=["model1", "model2"])
    result = [ft(r) for r in result]
    assert len(result) == 2
    assert result[0].name == "task1"
    assert result[0].model
    assert result[0].model.name == "model1"
    assert result[1].name == "task1"
    assert result[1].model
    assert result[1].model.name == "model2"


def test_task_x_names():
    result = tasks_with(task=["task1", "task2"], model="model1")
    result = [ft(r) for r in result]
    assert len(result) == 2
    assert result[0].name == "task1"
    assert result[0].model
    assert result[0].model.name == "model1"
    assert result[1].name == "task2"
    assert result[1].model
    assert result[1].model.name == "model1"


def test_duplicate_raises():
    with pytest.raises(ValueError, match="model provided in both base and matrix"):
        tasks_matrix(
            task=FlowTask(name="task1", model=FlowModel(name="model1")),
            model=["model2"],
        )


def test_nested_types():
    result = tasks_matrix(
        task=FlowTask(name="task1"),
        model=[
            {
                "name": "model1",
                "config": {"system_message": "test system message"},
            },
            {"name": "model2"},
        ],
    )
    result = [ft(r) for r in result]
    assert len(result) == 2
    assert result[0].name == "task1"
    assert result[0].model
    assert result[0].model.name == "model1"
    assert result[1].name == "task1"
    assert result[1].model
    assert result[1].model.name == "model2"


def test_nested_types_error():
    with pytest.raises(ValidationError):
        tasks_matrix(
            task=FlowTask(name="task1"),
            model=[
                {
                    "name": "model1",
                    "config": [{"system_message": "test system message"}],
                },  # type: ignore
                {"name": "model2"},
            ],
        )


def test_configs():
    result = tasks_matrix(
        task=FlowTask(name="task1", model=FlowModel(name="model1")),
        config=configs_matrix(config={}, system_message=["message1", "message2"]),
    )
    result = [ft(r) for r in result]
    assert len(result) == 2
    assert result[0].name == "task1"
    assert result[0].config
    assert result[0].config.system_message == "message1"
    assert result[1].name == "task1"
    assert result[1].config
    assert result[1].config.system_message == "message2"
