"""ReAct agent: alternate between thinking and acting until finished."""
from app.agent.base import BaseAgent
from app.logger import logger


class ReActAgent(BaseAgent):
    """Agent that loops think() -> act() until the task is finished."""

    async def step(self) -> str:
        should_continue = await self.think()
        if not should_continue:
            return "Thinking complete - no further action"
        return await self.act()
