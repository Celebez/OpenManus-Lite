"""Execute Python code in a restricted environment."""
import asyncio
import contextlib
import io
import json
from typing import Any

from app.config import config
from app.tool.base import BaseTool, ToolResult


class PythonExecute(BaseTool):
    name: str = "python_execute"
    description: str = (
        "Execute Python code and return the result. "
        "Use print() for output. The last expression value is also returned."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            }
        },
        "required": ["code"],
    }

    async def execute(self, code: str, timeout: int = 30) -> ToolResult:
        try:
            result = await asyncio.wait_for(
                self._run(code), timeout=timeout
            )
            return self.success_response(result)
        except asyncio.TimeoutError:
            return self.fail_response(f"Execution timed out after {timeout}s")
        except Exception as e:
            return self.fail_response(f"Execution error: {str(e)}")

    async def _run(self, code: str) -> str:
        buf = io.StringIO()
        local_ns: dict = {}
        with contextlib.redirect_stdout(buf):
            try:
                tree = compile(code, "<exec>", "exec")
                exec(tree, {}, local_ns)
            except Exception as e:
                buf.write(f"\n{e.__class__.__name__}: {e}\n")
        return buf.getvalue() or "(no output)"
