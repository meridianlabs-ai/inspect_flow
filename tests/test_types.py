from __future__ import annotations

from inspect_flow._types.flow_types import (
    AgentConfig,
    FlowConfig,
    Matrix,
    MatrixDict,
    ModelConfig,
    SolverConfig,
    TaskConfig,
    agent_config,
    flow_config,
    matrix,
    model_config,
    solver_config,
    task_config,
)

amatrix: MatrixDict = {"tasks": []}


def no_errors() -> None:
    _config = flow_config({"matrix": [{"tasks": ["one_module/one_task"]}]})
    _config = FlowConfig(matrix=[matrix({"tasks": []})])
    _config = FlowConfig(matrix=[Matrix(tasks=[task_config({"name": "dict"})])])
    _config = FlowConfig(
        matrix=[Matrix(tasks=[TaskConfig(name="class"), task_config({"name": "dict"})])]
    )
    _config = FlowConfig(matrix=[Matrix(tasks=[])])


# Should have pylance errors
def errors() -> None:
    _matrixdict: MatrixDict = {}  # pyright: ignore[reportAssignmentType]
    _config = flow_config({"matrix": [Matrix(tasks=[Matrix(tasks=[])])]})  # pyright: ignore[reportArgumentType]
    _config = flow_config({"matrix": [TaskConfig()]})  # pyright: ignore[reportArgumentType]
    _config = FlowConfig(matrix=[Matrix(tasks=[]), TaskConfig()])  # pyright: ignore[reportArgumentType]
    _config = FlowConfig(bad=None, matrix=[])  # pyright: ignore[reportCallIssue]


def test_contructors():
    task_name = "one_module/one_task"
    model_name = "module/model"

    config = task_config({"name": task_name, "models": [model_name]})
    assert config.name == task_name
    assert config.models
    assert config.models[0].name == model_name
    config = TaskConfig(name=task_name, models=[ModelConfig(name=model_name)])
    assert config.name == task_name
    assert config.models
    assert config.models[0].name == model_name

    config = model_config({"name": model_name, "role": "mark"})
    assert config.name == model_name
    config = ModelConfig(name=model_name, role="mark")
    assert config.name == model_name

    config = solver_config({"name": model_name, "args": [{"temperature": 0.5}]})
    assert config.name == model_name
    config = SolverConfig(name=model_name)
    assert config.name == model_name

    config = agent_config({"name": model_name, "args": [{"temperature": 0.7}]})
    assert config.name == model_name
    config = AgentConfig(name=model_name)
    assert config.name == model_name


def test_task_from_string():
    task_name = "one_module/one_task"
    config = flow_config({"matrix": [{"tasks": [task_name]}]})
    assert config.matrix[0].tasks[0].name == task_name


def test_task_from_dict():
    task_name = "one_module/one_task"
    config = flow_config({"matrix": [{"tasks": [{"name": task_name}]}]})
    assert config.matrix[0].tasks[0].name == task_name


def test_model_from_string():
    model_name = "module/model"
    model_role = "mark"
    model_name2 = "module/model2"
    config = flow_config(
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

    config = flow_config(
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
    config = flow_config(
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

    config = flow_config(
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
