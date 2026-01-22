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
    FlowSpec,
    FlowTask,
)


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


# Task without the decorator
def b_task(task_arg: float = 0.0) -> Task:
    return Task()


model = get_model("mockllm/model")
spec = FlowSpec(
    log_dir="logs",
    tasks=[
        a_task(),
        FlowTask(factory=a_task, model=model, solver=[a_solver()], scorer=a_scorer()),
        FlowTask(factory=b_task, model=model, solver=a_agent(), scorer=a_scorer()),
    ],
)
