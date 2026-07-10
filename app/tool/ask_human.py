"""Ask the human for input (in interactive mode)."""
from typing import Any

from app.tool.base import BaseTool, ToolResult


class AskHuman(BaseTool):
    name: str = "ask_human"
    description: str = "Ask the human a question and wait for a reply."
    parameters: dict = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask."}
        },
        "required": ["question"],
    }

    async def execute(self, question: str) -> ToolResult:
        try:
            answer = input(f"[AskHuman] {question}\n> ")
        except EOFError:
            answer = ""
        return self.success_response(answer or "(no answer)")
