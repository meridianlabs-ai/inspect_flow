from typing import Any

import pytest
from botocore.client import BaseClient
from inspect_ai import Task, task
from inspect_ai.agent import Agent, AgentState, agent
from inspect_ai.model import Model, get_model
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowDefaults,
    FlowEpochs,
    FlowExtraArgs,
    FlowFactory,
    FlowModel,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowTask,
)
from inspect_flow._util.pydantic_util import model_dump
from rich.console import Console

from tests.local_eval.src.local_eval.tools import add

task_name = "tests/local_eval/src/local_eval/noop.py@noop"  # task from a file relative to the base_dir


def test_task_not_resolved() -> None:
    for spec in [
        FlowSpec(tasks=[task_name]),
        FlowSpec(defaults=FlowDefaults(), tasks=[FlowTask(name=task_name)]),
        FlowSpec(tasks=[FlowTask(name=task_name, model="mockllm/mock-llm")]),
        FlowSpec(tasks=[FlowTask(name=task_name, solver="inspect/solver")]),
    ]:
        with pytest.raises(ValueError) as e:
            instantiate_tasks(spec=spec, base_dir=".")
        assert "config must be resolved before calling instantiate_task" in str(e.value)


def test_missing_model_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, model=FlowModel()),
        ]
    )
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Model name is required." in str(e.value)


def test_missing_scorer_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, scorer=FlowScorer()),
        ]
    )
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Scorer name is required." in str(e.value)


def test_none_scorer() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, scorer=None),
        ]
    )
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.scorer is None


def test_unresolved_solver() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, solver=["inspect/solver"]),
        ]
    )
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Solver should have been resolved. Solver: inspect/solver" in str(e.value)


def test_missing_solver_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, solver=FlowSolver()),
        ]
    )
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Solver name is required." in str(e.value)


def test_missing_agent_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, solver=FlowAgent()),
        ]
    )
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Agent name is required." in str(e.value)


def test_flow_epochs() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, epochs=FlowEpochs(epochs=3, reducer="median")),
        ]
    )
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.epochs == 3
    assert tasks[0].task.epochs_reducer
    assert (
        tasks[0].task.epochs_reducer[0].__qualname__ == "median_score.<locals>.reduce"
    )


def test_file_not_found() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name="missing_file.py@task_name"),
        ]
    )
    with pytest.raises(FileNotFoundError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "No such file or directory:" in str(e.value)
    assert "missing_file.py" in str(e.value)


def test_missing_task_name() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(),
        ]
    )
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Task name is required." in str(e.value)


def test_missing_task() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name="unregistered_task"),
        ]
    )
    with pytest.raises(LookupError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "unregistered_task" in str(e.value)


def test_agent_tools() -> None:
    agent_tools = None

    @agent
    def my_agent(tools: list[Any]) -> Agent:
        nonlocal agent_tools
        agent_tools = tools

        async def execute(state: AgentState) -> AgentState:
            return state

        return execute

    spec = FlowSpec(
        tasks=[
            FlowTask(
                name=task_name,
                solver=FlowAgent(
                    name="my_agent",
                    args={"tools": [add()]},
                ),
            )
        ],
    )
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.solver
    assert agent_tools is not None
    assert len(agent_tools) == 1
    assert callable(agent_tools[0])
    assert agent_tools[0].__qualname__ == "add.<locals>.execute"

    # Test that dumping and re-loading the spec works
    agent_tools = None
    dump = model_dump(spec)
    spec = FlowSpec.model_validate(dump)
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.solver
    assert agent_tools is not None
    assert len(agent_tools) == 1
    assert callable(agent_tools[0])
    assert agent_tools[0].__qualname__ == "add.<locals>.execute"


def test_additional_args_agent_tools() -> None:
    agent_tools = None

    @agent
    def my_agent(tools: list[Any]) -> Agent:
        nonlocal agent_tools
        agent_tools = tools

        async def execute(state: AgentState) -> AgentState:
            return state

        return execute

    spec = FlowSpec(
        tasks=[
            FlowTask(
                name=task_name,
                extra_args=FlowExtraArgs(agent={"tools": [add()]}),
                solver=FlowAgent(name="my_agent"),
            )
        ],
    )
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.solver
    assert agent_tools is not None
    assert len(agent_tools) == 1
    assert callable(agent_tools[0])
    assert agent_tools[0].__qualname__ == "add.<locals>.execute"


def test_additional_args_agent_tools_dict() -> None:
    agent_tools = None

    @agent
    def my_agent(model: Model, tools: dict[str, list[Any]]) -> Agent:
        assert model.name == "mock-llm1"
        nonlocal agent_tools
        agent_tools = tools

        async def execute(state: AgentState) -> AgentState:
            return state

        return execute

    spec = FlowSpec(
        tasks=[
            FlowTask(
                name=task_name,
                extra_args=FlowExtraArgs(
                    agent={
                        "model": get_model("mockllm/mock-llm1"),
                        "tools": {"math": [add()]},
                    }
                ),
                solver=FlowAgent(name="my_agent"),
            )
        ],
    )
    dump = model_dump(spec)
    spec = FlowSpec.model_validate(dump)
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.solver
    assert agent_tools is not None
    assert len(agent_tools) == 1
    assert callable(agent_tools["math"][0])
    assert agent_tools["math"][0].__qualname__ == "add.<locals>.execute"


def test_instantiate_s3(mock_s3: BaseClient) -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(factory="./tests/local_eval/src/local_eval/noop.py@noop"),
        ]
    )
    tasks = instantiate_tasks(spec=spec, base_dir="s3://test-bucket/configs/")
    assert len(tasks) == 1
    assert tasks[0].task.name == "noop"


def test_tags() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name=task_name, tags=["foo", "bar"]),
        ]
    )
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.tags == ["foo", "bar"]


def test_factory_str() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(factory=FlowFactory(factory=task_name)),
        ]
    )
    tasks = instantiate_tasks(spec=spec, base_dir=".")
    assert len(tasks) == 1
    assert tasks[0].task.name == "noop"


@task
def instantiate_error_task() -> Task:
    raise ValueError("Instantiation Error")


def test_534_instantiate_error(recording_console: Console) -> None:
    spec = FlowSpec(tasks=[FlowTask(name="instantiate_error_task")])
    with pytest.raises(ValueError) as e:
        instantiate_tasks(spec=spec, base_dir=".")
    assert "Instantiation Error" in str(e.value)
    out = recording_console.export_text()
    assert "Instantiation Error" in out
    assert "instantiate_error_task" in out
