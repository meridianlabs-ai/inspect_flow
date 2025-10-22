from __future__ import annotations

from inspect_flow._types.flow_types import (
    FlowConfig,
    Matrix,
    MatrixDict,
    SolverConfig,
    TaskConfig,
)

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
    model_role = "mark"
    model_name2 = "module/model2"
    config = FlowConfig(
        {
            "matrix": [
                {
                    "tasks": ["module/task"],
                    "models": [model_name],
                    "model_roles": [{model_role: model_name2}],
                }
            ]
        }
    )
    assert config.matrix[0].models
    assert config.matrix[0].models[0].name == model_name
    assert config.matrix[0].model_roles
    assert config.matrix[0].model_roles[0][model_role] == model_name2

    config = FlowConfig(
        {
            "matrix": [
                {
                    "tasks": [
                        {
                            "name": "module/task",
                            "models": [model_name],
                            "model_roles": [{model_role: model_name2}],
                        }
                    ]
                }
            ]
        }
    )
    assert config.matrix[0].tasks[0].models
    assert config.matrix[0].tasks[0].models[0].name == model_name
    assert config.matrix[0].tasks[0].model_roles
    assert config.matrix[0].tasks[0].model_roles[0][model_role] == model_name2


def test_solver_from_string():
    solver_name = "module/solver"
    solver_name2 = "module/solver2"
    solver_name3 = "module/solver3"
    config = FlowConfig(
        {
            "matrix": [
                {
                    "tasks": ["module/task"],
                    "solvers": [solver_name, [solver_name2, solver_name3]],
                }
            ]
        }
    )
    assert config.matrix[0].solvers
    assert isinstance(config.matrix[0].solvers[0], SolverConfig)
    assert config.matrix[0].solvers[0].name == solver_name
    assert isinstance(config.matrix[0].solvers[1], list)
    assert config.matrix[0].solvers[1][0].name == solver_name2
    assert config.matrix[0].solvers[1][1].name == solver_name3

    config = FlowConfig(
        {
            "matrix": [
                {
                    "tasks": [
                        {
                            "name": "module/task",
                            "solvers": [solver_name, [solver_name2, solver_name3]],
                        }
                    ],
                }
            ]
        }
    )
    assert config.matrix[0].tasks[0].solvers
    assert isinstance(config.matrix[0].tasks[0].solvers[0], SolverConfig)
    assert config.matrix[0].tasks[0].solvers[0].name == solver_name
    assert isinstance(config.matrix[0].tasks[0].solvers[1], list)
    assert config.matrix[0].tasks[0].solvers[1][0].name == solver_name2
    assert config.matrix[0].tasks[0].solvers[1][1].name == solver_name3
