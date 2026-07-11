"""Manus: the default general-purpose agent."""

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.bash import Bash
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.webfetch import WebFetch

# Use the real browser only if Playwright/Chromium is available; otherwise
# fall back to the lightweight zero-dependency web fetcher (Termux, etc.).
from app.tool import BROWSER_AVAILABLE, Browser

_WEB_TOOL = Browser() if BROWSER_AVAILABLE else WebFetch()


class Manus(ToolCallAgent):
    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools."

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            Bash(),
            StrReplaceEditor(),
            _WEB_TOOL,
            AskHuman(),
            Terminate(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    @model_validator(mode="after")
    def post_init(self) -> "Manus":
        return self
