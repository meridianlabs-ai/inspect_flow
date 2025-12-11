from __future__ import annotations

import yaml
from inspect_ai.model import GenerateConfig
from inspect_flow import (
    FlowDefaults,
    FlowModel,
    FlowSpec,
    FlowTask,
    configs_matrix,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._types.flow_types import FlowAgent, not_given
from inspect_flow._util.args import MODEL_DUMP_ARGS
from pydantic_core import to_jsonable_python


def test_task_from_string():
    task_name = "one_module/one_task"
    config = FlowSpec(tasks=[task_name])
    assert config.tasks
    assert len(config.tasks) == 1
    assert config.tasks[0] == task_name


def test_model_from_string():
    model_name = "module/model"
    model_role = "mark"
    model_name2 = "module/model2"
    config = FlowSpec(
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
    config = FlowSpec(
        tasks=[
            FlowTask(name="module/task", solver=solver_name),
            FlowTask(name="module/task", solver=[solver_name2, solver_name3]),
        ],
    )
    assert config.tasks
    assert isinstance(config.tasks[0], FlowTask)
    assert config.tasks[0].solver
    assert config.tasks[0].solver == solver_name
    assert isinstance(config.tasks[1], FlowTask)
    assert isinstance(config.tasks[1].solver, list)
    assert config.tasks[1].solver[0] == solver_name2
    assert config.tasks[1].solver[1] == solver_name3


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


def test_agent_from_yaml():
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="module/task",
                solver=FlowAgent(name="module/agent"),
            )
        ]
    )
    dump = config_to_yaml(spec)
    spec2 = FlowSpec.model_validate(yaml.safe_load(dump), extra="forbid")
    assert spec2.tasks
    assert len(spec2.tasks) == 1
    assert isinstance(spec2.tasks[0], FlowTask)
    assert isinstance(spec2.tasks[0].solver, FlowAgent)
    assert spec2 == spec


def test_task_none_model_name():
    task = FlowTask(name="module/task")
    assert task.model_name is None
    task = FlowTask(name="module/task", model=FlowModel())
    assert task.model_name == not_given
