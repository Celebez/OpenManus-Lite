"""Run shell commands."""
import asyncio
import shlex
from typing import Any

from app.tool.base import BaseTool, ToolResult


class Bash(BaseTool):
    name: str = "bash"
    description: str = "Run a shell command and return its stdout/stderr."
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to run.",
            }
        },
        "required": ["command"],
    }

    async def execute(self, command: str, timeout: int = 60) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            text = out.decode("utf-8", errors="replace")
            return self.success_response(f"[exit {proc.returncode}]\n{text}")
        except asyncio.TimeoutError:
            return self.fail_response(f"Command timed out after {timeout}s")
        except Exception as e:
            return self.fail_response(f"Shell error: {str(e)}")
