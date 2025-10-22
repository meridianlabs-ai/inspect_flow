from __future__ import annotations

from inspect_flow._types.flow_types import FlowConfig, Matrix, MatrixDict, TaskConfig

matrix: MatrixDict = {"tasks": []}


def no_errors() -> None:
    config = FlowConfig({"matrix": [{"tasks": ["one_module/one_task"]}]})
    config = FlowConfig(matrix=[{"tasks": []}])
    config = FlowConfig(matrix=[Matrix(tasks=[{"name": "dict"}])])
    config = FlowConfig(
        matrix=[Matrix(tasks=["string", TaskConfig(name="class"), {"name": "dict"}])]
    )
    config = FlowConfig(matrix=[Matrix(tasks=[])])


# Should have pylance errors
def errors() -> None:
    matrix: MatrixDict = {}
    matrix = Matrix({"tasks": []})
    config = FlowConfig({"matrix": [Matrix(tasks=[Matrix(tasks=[])])]})
    config = FlowConfig({"matrix": [TaskConfig()]})
    config = FlowConfig(matrix=[Matrix(tasks=[]), TaskConfig()])
    config = FlowConfig(bad=None)


def foo(config: FlowConfig) -> None:
    value = config.matrix[0].args


def test_task_from_string():
    task_name = "one_module/one_task"
    config = FlowConfig({"matrix": [{"tasks": [task_name]}]})
    assert config.matrix[0].tasks[0].name == task_name


def test_task_from_dict():
    task_name = "one_module/one_task"
    config = FlowConfig({"matrix": [{"tasks": [{"name": task_name}]}]})
    assert config.matrix[0].tasks[0].name == task_name


def test_model_from_string():
    model_name = "module/model"
    config = FlowConfig(
        {
            "matrix": [
                {"tasks": [TaskConfig(name="module/task")], "models": [model_name]}
            ]
        }
    )
    assert config.matrix[0].models
    assert config.matrix[0].models[0].name == model_name
