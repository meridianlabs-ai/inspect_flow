from unittest.mock import MagicMock, patch

import pytest
from inspect_ai import Task, task
from inspect_ai.agent import Agent, AgentState, agent
from inspect_ai.model import get_model
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Scorer,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowModel,
    FlowSolver,
    FlowSpec,
    FlowTask,
    tasks_matrix,
    tasks_with,
)
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.flow_types import FlowScorer
from inspect_flow._util.pydantic_util import model_dump
from inspect_flow.api import run

from tests.test_helpers.log_helpers import init_test_logs, verify_test_logs


@solver
def a_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate):
        # do something useful with state (possibly
        # calling generate for more advanced solvers)
        # then return the state
        return state

    return solve


@scorer(metrics=[accuracy(), stderr()])
def a_scorer(ignore_case: bool = True) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        answer = state.output.completion
        if ignore_case:
            correct = answer.lower().rfind(target.text.lower()) != -1
        else:
            correct = answer.rfind(target.text) != -1
        return Score(value=CORRECT if correct else INCORRECT, answer=answer)

    return score


@agent
def a_agent() -> Agent:
    async def execute(state: AgentState) -> AgentState:
        return state

    return execute


@task
def a_task(task_arg: float = 0.0) -> Task:
    return Task()


def b_task(task_arg: float = 0.0) -> Task:
    return Task()


def test_inspect_objects(mock_eval_set: MagicMock) -> None:
    model = get_model("mockllm/model")
    spec = FlowSpec(
        log_dir=init_test_logs(),
        tasks=[
            a_task(),
            FlowTask(
                factory=a_task, model=model, solver=[a_solver()], scorer=a_scorer()
            ),
        ],
    )
    with patch("inspect_flow._launcher.inproc.write_flow_requirements"):
        run(spec=spec)

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert isinstance(tasks_arg[0], Task)


def test_inspect_object_defaults(mock_eval_set: MagicMock) -> None:
    model = get_model("mockllm/model")
    spec = FlowSpec(
        log_dir=init_test_logs(),
        defaults=FlowDefaults(
            agent=FlowAgent(args={"agent_arg": 123}),
            model=FlowModel(model_args={"model_arg": "value"}),
            solver=FlowSolver(args={"solver_arg": True}),
            task=FlowTask(args={"task_arg": 3.14}),
        ),
        tasks=[
            a_task(),
            FlowTask(
                factory=a_task, model=model, solver=[a_solver()], scorer=a_scorer()
            ),
        ],
    )
    with patch("inspect_flow._launcher.inproc.write_flow_requirements"):
        run(spec=spec)

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert isinstance(tasks_arg[0], Task)


def test_inspect_object_includes(mock_eval_set: MagicMock) -> None:
    model = get_model("mockllm/model")
    include = FlowSpec(
        log_dir=init_test_logs(),
        defaults=FlowDefaults(
            agent=FlowAgent(args={"agent_arg": 123}),
            model=FlowModel(model_args={"model_arg": "value"}),
            solver=FlowSolver(args={"solver_arg": True}),
            task=FlowTask(args={"task_arg": 3.14}),
        ),
    )
    spec = FlowSpec(
        includes=[include],
        log_dir=init_test_logs(),
        tasks=[
            a_task(),
            FlowTask(
                factory=a_task, model=model, solver=[a_solver()], scorer=a_scorer()
            ),
        ],
    )
    with patch("inspect_flow._launcher.inproc.write_flow_requirements"):
        run(spec=spec)

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 2
    assert isinstance(tasks_arg[0], Task)


def test_inspect_object_with(mock_eval_set: MagicMock) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        tasks=[
            a_task(),
            *tasks_with(
                task=[FlowTask(factory=a_task), FlowTask(factory=b_task)],
                model="mockllm/model",
            ),
            *tasks_with(
                task=[FlowTask(factory=a_task), FlowTask(factory=b_task)],
                model=get_model("mockllm/model2"),
            ),
        ],
    )
    with patch("inspect_flow._launcher.inproc.write_flow_requirements"):
        run(spec=spec)

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 5
    for i, t in enumerate(tasks_arg):
        assert isinstance(t, Task)
        if i == 0:
            assert t.model is None
        elif i < 3:
            assert t.model
            assert t.model.name == "model"
        else:
            assert t.model
            assert t.model.name == "model2"


def test_inspect_object_matrix(mock_eval_set: MagicMock) -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        tasks=tasks_matrix(
            task=[FlowTask(factory=a_task), FlowTask(factory=b_task)],
            model=["mockllm/model", get_model("mockllm/model2")],
        ),
    )
    with patch("inspect_flow._launcher.inproc.write_flow_requirements"):
        run(spec=spec)

    mock_eval_set.assert_called_once()
    call_args = mock_eval_set.call_args
    tasks_arg = call_args.kwargs["tasks"]
    assert len(tasks_arg) == 4
    for i, t in enumerate(tasks_arg):
        assert isinstance(t, Task)
        if not i % 2:
            assert t.model
            assert t.model.name == "model"
        else:
            assert t.model
            assert t.model.name == "model2"


def test_inspect_object_instantiation() -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[
            FlowTask(
                factory=a_task,
                model=FlowModel(factory=lambda: get_model("mockllm/model")),
                solver=[FlowSolver(factory=a_solver)],
                scorer=FlowScorer(factory=a_scorer),
            ),
            FlowTask(
                factory=b_task,
                model="mockllm/model2",
                solver=FlowAgent(factory=a_agent),
            ),
            FlowTask(
                factory=a_task,
                model="mockllm/model3",
                scorer=[a_scorer()],
                solver=a_solver(),
            ),
        ],
    )
    with (
        patch("inspect_flow._launcher.inproc.write_flow_requirements"),
    ):
        run(spec=spec)
    verify_test_logs(spec, log_dir)


def test_model_dump_no_registry() -> None:
    spec = FlowSpec(
        tasks=[b_task()],
    )
    dump = model_dump(spec)
    assert "<inspect_ai._eval.task.task.Task object at" in dump["tasks"][0]


def test_factory_instantiation() -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[
            FlowTask(
                factory=a_task,
                model="mockllm/model",
            ),
        ],
    )
    dump = model_dump(spec)
    spec = FlowSpec.model_validate(dump)
    run_eval_set(spec=(spec), base_dir=".")
    verify_test_logs(spec, log_dir)


def test_559_factory_name() -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[
            FlowTask(
                name="custom_task_name",
                factory=a_task,
                model="mockllm/model",
            ),
        ],
    )
    result = run_eval_set(spec=(spec), base_dir=".")
    logs = result[1]
    assert len(logs) == 1
    assert logs[0].eval.task == "custom_task_name"
    verify_test_logs(spec, log_dir)


def test_559_factory_name_after_dump() -> None:
    log_dir = init_test_logs()
    spec = FlowSpec(
        log_dir=log_dir,
        tasks=[
            FlowTask(
                name="custom_task_name",
                factory=a_task,
                model="mockllm/model",
            ),
        ],
    )
    dump = model_dump(spec)
    spec = FlowSpec.model_validate(dump)
    result = run_eval_set(spec=(spec), base_dir=".")
    logs = result[1]
    assert len(logs) == 1
    assert logs[0].eval.task == "custom_task_name"
    verify_test_logs(spec, log_dir)


def test_duplicate_task_objects() -> None:
    spec = FlowSpec(
        log_dir=init_test_logs(),
        tasks=[a_task(), a_task()],
    )
    with (
        pytest.raises(ValueError) as e,
        patch("inspect_flow._launcher.inproc.write_flow_requirements"),
    ):
        run(spec=spec)
    assert "Duplicate task found" in str(e.value)
    assert "<inspect_ai._eval.task.task.Task object at" in str(e.value)
