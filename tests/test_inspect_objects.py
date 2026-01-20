from unittest.mock import patch

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
)
from inspect_flow.api import run


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


def test_inspect_objects() -> None:
    model = get_model("mockllm/model")
    spec = FlowSpec(
        log_dir="logs",
        tasks=[
            a_task(),
            FlowTask(
                factory=a_task, model=model, solver=[a_solver()], scorer=a_scorer()
            ),
        ],
    )
    with (
        patch("inspect_flow._runner.run.eval_set") as mock_eval_set,
        patch("inspect_flow._launcher.inproc.write_flow_requirements"),
    ):
        run(spec=spec)

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert isinstance(tasks_arg[0], Task)


def test_inspect_object_defaults() -> None:
    model = get_model("mockllm/model")
    spec = FlowSpec(
        log_dir="logs",
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
    with (
        patch("inspect_flow._runner.run.eval_set") as mock_eval_set,
        patch("inspect_flow._launcher.inproc.write_flow_requirements"),
    ):
        run(spec=spec)

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert isinstance(tasks_arg[0], Task)


def test_inspect_object_includes() -> None:
    model = get_model("mockllm/model")
    include = FlowSpec(
        log_dir="logs",
        defaults=FlowDefaults(
            agent=FlowAgent(args={"agent_arg": 123}),
            model=FlowModel(model_args={"model_arg": "value"}),
            solver=FlowSolver(args={"solver_arg": True}),
            task=FlowTask(args={"task_arg": 3.14}),
        ),
    )
    spec = FlowSpec(
        includes=[include],
        log_dir="logs",
        tasks=[
            a_task(),
            FlowTask(
                factory=a_task, model=model, solver=[a_solver()], scorer=a_scorer()
            ),
        ],
    )
    with (
        patch("inspect_flow._runner.run.eval_set") as mock_eval_set,
        patch("inspect_flow._launcher.inproc.write_flow_requirements"),
    ):
        run(spec=spec)

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 2
        assert isinstance(tasks_arg[0], Task)
