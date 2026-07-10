"""Terminate the agent run."""

from app.tool.base import BaseTool, ToolResult


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = "Terminate the agent run and report the final result."
    parameters: dict = {
        "type": "object",
        "properties": {
            "result": {
                "type": "string",
                "description": "Final result to report to the user.",
            }
        },
        "required": ["result"],
    }

    async def execute(self, result: str) -> ToolResult:
        return self.success_response(result)
