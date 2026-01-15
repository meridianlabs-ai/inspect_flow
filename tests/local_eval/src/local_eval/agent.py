from inspect_ai.agent import Agent, AgentState, agent


@agent
def test_agent() -> Agent:
    async def execute(state: AgentState) -> AgentState:
        return state

    return execute
