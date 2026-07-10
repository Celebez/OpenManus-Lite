"""Abstract base agent with a step-based execution loop."""
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field

from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory, Message


class BaseAgent(BaseModel, ABC):
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    system_prompt: Optional[str] = Field(None, description="System-level instruction prompt")
    next_step_prompt: Optional[str] = Field(None, description="Prompt for next action")

    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(default=AgentState.IDLE, description="Current state")

    max_steps: int = Field(default=15, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")
    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR
            raise e
        finally:
            self.state = previous_state

    def update_memory(self, role, content: str, base64_image: Optional[str] = None, **kwargs):
        mapping = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda c, **kw: Message.tool_message(c, **kw),
        }
        if role not in mapping:
            raise ValueError(f"Unsupported message role: {role}")
        kwargs = {"base64_image": base64_image, **(kwargs if role == "tool" else {})}
        self.memory.add_message(mapping[role](content, **kwargs))

    async def run(self, request: Optional[str] = None) -> str:
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")
        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()
                if self.is_stuck():
                    self.handle_stuck_state()
                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
        return "\n".join(results) if results else "No steps executed"

    @abstractmethod
    async def step(self) -> str:
        pass

    def handle_stuck_state(self):
        stuck_prompt = "Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"

    def is_stuck(self) -> bool:
        if len(self.memory.messages) < 2:
            return False
        last = self.memory.messages[-1]
        if not last.content:
            return False
        dup = sum(
            1
            for m in reversed(self.memory.messages[:-1])
            if m.role == "assistant" and m.content == last.content
        )
        return dup >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        self.memory.messages = value
