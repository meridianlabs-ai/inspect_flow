from __future__ import annotations

from inspect_flow import (
    FlowAgent,
    FlowConfig,
    FlowMatrix,
    FlowMatrixDict,
    FlowModel,
    FlowSolver,
    FlowTask,
    flow_agent,
    flow_config,
    flow_matrix,
    flow_model,
    flow_solver,
    flow_task,
)


def no_errors() -> None:
    _config = flow_config({"matrix": [{"tasks": ["one_module/one_task"]}]})
    _config = FlowConfig(matrix=[flow_matrix({"tasks": []})])
    _config = FlowConfig(matrix=[FlowMatrix(tasks=[flow_task({"name": "dict"})])])
    _config = FlowConfig(
        matrix=[FlowMatrix(tasks=[FlowTask(name="class"), flow_task({"name": "dict"})])]
    )
    _config = FlowConfig(matrix=[FlowMatrix(tasks=[])])


# Should have pylance errors
def errors() -> None:
    _matrixdict: FlowMatrixDict = {}  # pyright: ignore[reportAssignmentType]
    _config = flow_config({"matrix": [FlowMatrix(tasks=[FlowMatrix(tasks=[])])]})  # pyright: ignore[reportArgumentType]
    _config = flow_config({"matrix": [FlowTask()]})  # pyright: ignore[reportArgumentType]
    _config = FlowConfig(matrix=[FlowMatrix(tasks=[]), FlowTask()])  # pyright: ignore[reportArgumentType]
    _config = FlowConfig(bad=None, matrix=[])  # pyright: ignore[reportCallIssue]


def test_contructors():
    task_name = "one_module/one_task"
    model_name = "module/model"

    config = flow_task({"name": task_name, "models": [model_name]})
    assert config.name == task_name
    assert config.models
    assert config.models[0].name == model_name
    config = FlowTask(name=task_name, models=[FlowModel(name=model_name)])
    assert config.name == task_name
    assert config.models
    assert config.models[0].name == model_name

    config = flow_model({"name": model_name, "role": "mark"})
    assert config.name == model_name
    config = FlowModel(name=model_name, role="mark")
    assert config.name == model_name

    config = flow_solver({"name": model_name, "args": [{"temperature": 0.5}]})
    assert config.name == model_name
    config = FlowSolver(name=model_name)
    assert config.name == model_name

    config = flow_agent({"name": model_name, "args": [{"temperature": 0.7}]})
    assert config.name == model_name
    config = FlowAgent(name=model_name)
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
    assert isinstance(config.matrix[0].solvers[0], FlowSolver)
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
    assert isinstance(config.matrix[0].tasks[0].solvers[0], FlowSolver)
    assert config.matrix[0].tasks[0].solvers[0].name == solver_name
    assert isinstance(config.matrix[0].tasks[0].solvers[1], list)
    assert config.matrix[0].tasks[0].solvers[1][0].name == solver_name2
    assert config.matrix[0].tasks[0].solvers[1][1].name == solver_name3


def test_single_items():
    flow_config({"dependencies": "single_dependency", "matrix": [{"tasks": []}]})
    flow_config({"matrix": {"tasks": []}})

    flow_matrix({"args": {}, "tasks": {"name": "task_name"}})
    flow_matrix({"tasks": {"name": "task_name"}})
    flow_matrix({"models": "model_name", "tasks": {"name": "task_name"}})
    flow_matrix({"models": {"name": "model_name"}, "tasks": {"name": "task_name"}})
    flow_matrix({"model_roles": {}, "tasks": {"name": "task_name"}})
    flow_matrix({"solvers": "solver_name", "tasks": {"name": "task_name"}})
    flow_matrix({"solvers": {"name": "solver_name"}, "tasks": {"name": "task_name"}})

    flow_task({"name": "task_name", "args": {}})
    flow_task({"name": "task_name", "model_roles": {}})
    flow_task({"name": "task_name", "models": "model_name"})
    flow_task({"name": "task_name", "models": {"name": "model_name"}})
    flow_task({"name": "task_name", "solvers": "solver_name"})
    flow_task({"name": "task_name", "solvers": {"name": "solver_name"}})

    flow_agent({"name": "agent_name", "args": {}})

    flow_solver({"name": "solver_name", "args": {}})

    flow_model({"name": "model_name", "config": {}})
