"""Multi-agent flow: a supervisor routes a task to specialised sub-agents.

Each sub-agent is a ToolCallAgent configured with its own tool set and system
prompt. The supervisor LLM decides which sub-agent should handle the request
(the ``delegate`` tool), collects the result, and calls ``finish`` when the
overall task is complete.
"""
from __future__ import annotations

import json
from typing import Dict, List

from app.agent.manus import Manus
from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt import SupervisorPrompt
from app.schema import AgentState, Message, Role, ToolChoice
from app.tool import (
    Bash,
    Browser,
    CreateChatCompletion,
    PythonExecute,
    StrReplaceEditor,
    Terminate,
    ToolCollection,
    WebFetch,
)
from app.tool.base import BaseTool, ToolResult

# Lightweight fallback when Playwright/Chromium isn't installed (Termux).
from app.tool import BROWSER_AVAILABLE

_WEB_TOOL = Browser() if BROWSER_AVAILABLE else WebFetch()


class CodingAgent(ToolCallAgent):
    name: str = "coding_agent"
    description: str = "Writes and runs code, edits files, executes shell commands."
    system_prompt: str = SupervisorPrompt.CODING
    available_tools: ToolCollection = ToolCollection(
        PythonExecute(), Bash(), StrReplaceEditor(), CreateChatCompletion(), Terminate()
    )


class ResearchAgent(ToolCallAgent):
    name: str = "research_agent"
    description: str = "Browses the web, reads pages, and summarises findings."
    system_prompt: str = SupervisorPrompt.RESEARCH
    available_tools: ToolCollection = ToolCollection(
        _WEB_TOOL, CreateChatCompletion(), Terminate()
    )


class BrowserAgent(ToolCallAgent):
    name: str = "browser_agent"
    description: str = "Drives a real browser to navigate, click, type, screenshot."
    system_prompt: str = SupervisorPrompt.BROWSER
    available_tools: ToolCollection = ToolCollection(
        _WEB_TOOL, CreateChatCompletion(), Terminate()
    )


class DelegateTool(BaseTool):
    name: str = "delegate"
    description: str = "Hand the task to a specialised sub-agent."
    parameters: dict = {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["coding_agent", "research_agent", "browser_agent"],
            },
            "task": {"type": "string"},
        },
        "required": ["agent", "task"],
    }

    async def execute(self, agent: str, task: str) -> ToolResult:
        return ToolResult(output="ok")


class FinishTool(BaseTool):
    name: str = "finish"
    description: str = "Return the final summary and stop."
    parameters: dict = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    }

    async def execute(self, summary: str = "") -> ToolResult:
        return ToolResult(output=summary or "done")


class Supervisor(Manus):
    """Routes tasks to sub-agents instead of acting on its own."""

    name: str = "supervisor"
    description: str = "Coordinates specialised sub-agents to solve a task."
    system_prompt: str = SupervisorPrompt.SUPERVISOR

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agents: Dict[str, ToolCallAgent] = {
            "coding_agent": CodingAgent(),
            "research_agent": ResearchAgent(),
            "browser_agent": BrowserAgent(),
        }
        self._delegated_results: List[str] = []

    async def _delegate(self, agent_name: str, task: str) -> str:
        agent = self.agents.get(agent_name)
        if agent is None:
            return f"Unknown sub-agent: {agent_name}"
        logger.info(f"Supervisor delegating to {agent_name}: {task[:80]}...")
        try:
            result = await agent.run(task)
        finally:
            if hasattr(agent, "cleanup"):
                await agent.cleanup()
        self._delegated_results.append(f"[{agent_name}] {result}")
        return result

    async def think(self) -> bool:
        """Supervisor decides: delegate to a sub-agent, finish, or act."""
        try:
            response = await self.llm.ask_tool(
                messages=self.memory.messages,
                system_msgs=[Message.system_message(self.system_prompt)],
                tools=[DelegateTool().to_param(), FinishTool().to_param()],
                tool_choice=ToolChoice.AUTO,
            )
        except Exception as e:
            logger.error(f"Supervisor LLM error: {e}")
            self.state = AgentState.FINISHED
            return False
        self.tool_calls = response.tool_calls if response and response.tool_calls else []
        content = response.content if response and response.content else ""
        if self.tool_calls:
            call = self.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            self.memory.add_message(
                Message(role=Role.ASSISTANT, content=content, tool_calls=self.tool_calls)
            )
            if name == "finish":
                self.state = AgentState.FINISHED
                self._final_summary = args.get("summary", content)
                return False
            # delegate is executed in act(); keep looping
            return True
        if content:
            self.memory.add_message(Message.assistant_message(content))
            return True
        return False

    async def act(self) -> str:
        if not self.tool_calls:
            return self.memory.messages[-1].content or "No action"
        command = self.tool_calls[0]
        name = command.function.name
        args = json.loads(command.function.arguments or "{}")
        if name == "finish":
            self.state = AgentState.FINISHED
            self._final_summary = args.get("summary", "")
            return self._final_summary or "Task finished."
        if name == "delegate":
            result = await self._delegate(args.get("agent", ""), args.get("task", ""))
            self.memory.add_message(
                Message.tool_message(result, name=name, tool_call_id=command.id)
            )
            return result
        return "Unknown supervisor action."
