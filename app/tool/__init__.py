"""Tool package exports."""
from app.tool.ask_human import AskHuman
from app.tool.base import BaseTool, CLIResult, ToolFailure, ToolResult
from app.tool.bash import Bash
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate
from app.tool.tool_collection import ToolCollection
from app.tool.webfetch import WebFetch

# Browser is optional: Playwright/Chromium is heavy and often unavailable
# (Termux, minimal containers). Import it lazily so the rest of the toolkit
# works without it. Set OML_NO_BROWSER=1 to force the lightweight fetcher
# even when Playwright is installed.
import os

_FORCE_NO_BROWSER = os.environ.get("OML_NO_BROWSER", "").lower() in ("1", "true", "yes")

if _FORCE_NO_BROWSER:
    Browser = None  # type: ignore
    BROWSER_AVAILABLE = False
else:
    try:
        from app.tool.browser import Browser  # type: ignore
        BROWSER_AVAILABLE = True
    except Exception:  # playwright not installed or chromium missing
        Browser = None  # type: ignore
        BROWSER_AVAILABLE = False

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolFailure",
    "CLIResult",
    "ToolCollection",
    "PythonExecute",
    "Bash",
    "StrReplaceEditor",
    "AskHuman",
    "CreateChatCompletion",
    "Terminate",
    "WebFetch",
    "Browser",
]
