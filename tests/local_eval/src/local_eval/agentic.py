from inspect_ai import Task, task

# from inspect_ai.solver import basic_agent, solver
from inspect_ai.agent import Agent, agent, react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import match
from inspect_ai.tool import Tool, tool


def base() -> Task:
    dataset = MemoryDataset(
        [Sample(input="Hello, print what tools you have access to!", target="Hello")]
    )

    return Task(
        dataset=dataset,
        scorer=match(),
    )


@task
def cyber_ctf_task() -> Task:
    return base()


@task
def re_bench() -> Task:
    return base()


@agent
def simple_agent(tools) -> Agent:
    return react(
        description="Simple agent",
        tools=tools,
    )


@tool
def simple_tool() -> Tool:
    async def execute(x: int, y: int) -> int:
        return x + y

    return execute
