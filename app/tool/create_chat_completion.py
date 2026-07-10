"""Expose the LLM itself as a tool (lets the agent call the model directly)."""
from typing import Any

from app.llm import LLM
from app.tool.base import BaseTool, ToolResult


class CreateChatCompletion(BaseTool):
    name: str = "create_chat_completion"
    description: str = "Call the language model with a prompt and return its completion."
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The prompt to send to the model."}
        },
        "required": ["prompt"],
    }

    async def execute(self, prompt: str, system: str = None) -> ToolResult:
        try:
            llm = LLM()
            resp = await llm.ask([{"role": "user", "content": prompt}],
                                  system_msgs=[{"role": "system", "content": system}] if system else None)
            return self.success_response(resp)
        except Exception as e:
            return self.fail_response(str(e))
