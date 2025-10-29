from inspect_flow._types.factories import tasks
from inspect_flow._types.flow_types import FlowTask


def test_tasks_x_models():
    result = tasks(matrix={"name": ["task1", "task2"], "model": ["model1", "model2"]})
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
    result = tasks(
        FlowTask(name="task1"),
        matrix={"model": ["model1", "model2"]},
    )
    assert len(result) == 2
    assert result[0].name == "task1"
    assert result[0].model
    assert result[0].model.name == "model1"
    assert result[1].name == "task1"
    assert result[1].model
    assert result[1].model.name == "model2"
