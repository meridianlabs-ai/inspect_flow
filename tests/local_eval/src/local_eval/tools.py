from typing import Any

from inspect_ai.agent import Agent, AgentState, agent
from inspect_ai.tool import Tool, ToolDef, tool


@tool
def add() -> Tool:
    async def execute(x: int, y: int):
        """
        Add two numbers.

        Args:
            x: First number to add.
            y: Second number to add.

        Returns:
            The sum of the two numbers.
        """
        return x + y

    return execute


@agent
def my_agent(tools: list[Any]) -> Agent:
    assert len(tools) == 1
    assert callable(tools[0])
    assert ToolDef(tools[0]).name == "add"

    async def execute(state: AgentState) -> AgentState:
        return state

    return execute
