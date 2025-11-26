from __future__ import annotations

from inspect_flow import (
    FlowDefaults,
    FlowJob,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
    configs_matrix,
)
from inspect_flow._types.flow_types import not_given
from inspect_flow._util.args import MODEL_DUMP_ARGS
from pydantic_core import to_jsonable_python


def test_task_from_string():
    task_name = "one_module/one_task"
    config = FlowJob(tasks=[task_name])
    assert config.tasks
    assert isinstance(config.tasks[0], FlowTask)
    assert config.tasks[0].name == task_name


def test_model_from_string():
    model_name = "module/model"
    model_role = "mark"
    model_name2 = "module/model2"
    config = FlowJob(
        tasks=[
            FlowTask(
                name="module/task",
                model=model_name,
                model_roles={model_role: model_name2},
            )
        ]
    )
    assert config.tasks
    assert isinstance(config.tasks[0], FlowTask)
    assert config.tasks[0].model
    assert config.tasks[0].model_name == model_name
    assert config.tasks[0].model_roles
    assert config.tasks[0].model_roles[model_role] == model_name2


def test_solver_from_string():
    solver_name = "module/solver"
    solver_name2 = "module/solver2"
    solver_name3 = "module/solver3"
    config = FlowJob(
        tasks=[
            FlowTask(name="module/task", solver=solver_name),
            FlowTask(name="module/task", solver=[solver_name2, solver_name3]),
        ],
    )
    assert config.tasks
    assert isinstance(config.tasks[0], FlowTask)
    assert config.tasks[0].solver
    assert isinstance(config.tasks[0].solver, FlowSolver)
    assert config.tasks[0].solver.name == solver_name
    assert isinstance(config.tasks[1], FlowTask)
    assert isinstance(config.tasks[1].solver, list)
    assert isinstance(config.tasks[1].solver[1], FlowSolver)
    assert isinstance(config.tasks[1].solver[0], FlowSolver)
    assert config.tasks[1].solver[0].name == solver_name2
    assert config.tasks[1].solver[1].name == solver_name3


def test_defaults():
    FlowDefaults(
        config=GenerateConfig(max_connections=50),
        model=FlowModel(config=GenerateConfig(temperature=0.3)),
    )


def test_none_in_list():
    configs = configs_matrix(reasoning_tokens=[None, 2048])
    assert len(configs) == 2
    assert configs[0].reasoning_tokens is None
    assert configs[1].reasoning_tokens == 2048


def test_task_not_given():
    task1 = FlowTask(name="module/task", model=None)
    task2 = FlowTask.model_validate(task1.model_dump(**MODEL_DUMP_ARGS))
    assert task2.model != not_given
    assert task2.epochs == not_given
    jsonable = to_jsonable_python(task1)
    task3 = FlowTask.model_validate(jsonable)
    assert task3.model != not_given
    assert task3.epochs == not_given
