from __future__ import annotations

from inspect_flow import (
    flow_agent,
    flow_config,
    flow_model,
    flow_solver,
    flow_task,
)
from inspect_flow.types import (
    FlowAgent,
    FlowConfig,
    FlowModel,
    FlowSolver,
    FlowTask,
)


def no_errors() -> None:
    _config = flow_config({"tasks": ["one_module/one_task"]})
    _config = FlowConfig(tasks=[])
    _config = FlowConfig(tasks=[flow_task({"name": "dict"})])
    _config = FlowConfig(tasks=[FlowTask(name="class"), flow_task({"name": "dict"})])


def test_contructors():
    task_name = "one_module/one_task"
    model_name = "module/model"

    config = flow_task({"name": task_name, "model": model_name})
    assert config.name == task_name
    assert config.model
    assert config.model.name == model_name
    config = FlowTask(name=task_name, model=FlowModel(name=model_name))
    assert config.name == task_name
    assert config.model
    assert config.model.name == model_name

    config = flow_model({"name": model_name, "role": "mark"})
    assert config.name == model_name
    config = FlowModel(name=model_name, role="mark")
    assert config.name == model_name

    config = flow_solver({"name": model_name, "args": {"temperature": 0.5}})
    assert config.name == model_name
    config = FlowSolver(name=model_name)
    assert config.name == model_name

    config = flow_agent({"name": model_name, "args": {"temperature": 0.7}})
    assert config.name == model_name
    config = FlowAgent(name=model_name)
    assert config.name == model_name


def test_task_from_string():
    task_name = "one_module/one_task"
    config = flow_config({"tasks": [task_name]})
    assert config.tasks[0].name == task_name


def test_task_from_dict():
    task_name = "one_module/one_task"
    config = flow_config({"tasks": [{"name": task_name}]})
    assert config.tasks[0].name == task_name


def test_model_from_string():
    model_name = "module/model"
    model_role = "mark"
    model_name2 = "module/model2"
    config = flow_config(
        {
            "tasks": [
                {
                    "name": "module/task",
                    "model": model_name,
                    "model_roles": {model_role: model_name2},
                }
            ]
        }
    )
    assert config.tasks[0].model
    assert config.tasks[0].model.name == model_name
    assert config.tasks[0].model_roles
    assert config.tasks[0].model_roles[model_role] == model_name2


def test_solver_from_string():
    solver_name = "module/solver"
    solver_name2 = "module/solver2"
    solver_name3 = "module/solver3"
    config = flow_config(
        {
            "tasks": [
                {"name": "module/task", "solver": solver_name},
                {"name": "module/task", "solver": [solver_name2, solver_name3]},
            ],
        }
    )
    assert config.tasks[0].solver
    assert isinstance(config.tasks[0].solver, FlowSolver)
    assert config.tasks[0].solver.name == solver_name
    assert isinstance(config.tasks[1].solver, list)
    assert config.tasks[1].solver[0].name == solver_name2
    assert config.tasks[1].solver[1].name == solver_name3


def test_single_items():
    flow_config({"dependencies": "single_dependency", "tasks": []})
    flow_config({"tasks": "task_name"})
    flow_config(
        {"tasks": [{"name": "task_name"}]}
    )  # TODO:ransom do we want to support a single task?

    flow_task({"name": "task_name", "args": {}})
    flow_task({"name": "task_name", "model_roles": {}})
    flow_task({"name": "task_name", "model": "model_name"})
    flow_task({"name": "task_name", "model": {"name": "model_name"}})
    flow_task({"name": "task_name", "solver": "solver_name"})
    flow_task({"name": "task_name", "solver": {"name": "solver_name"}})

    flow_agent({"name": "agent_name", "args": {}})

    flow_solver({"name": "solver_name", "args": {}})

    flow_model({"name": "model_name", "config": {}})
