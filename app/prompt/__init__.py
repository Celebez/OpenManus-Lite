from app.prompt.manus import SYSTEM_PROMPT, NEXT_STEP_PROMPT
from app.prompt.toolcall import SYSTEM_PROMPT as TOOLCALL_SYSTEM_PROMPT
from app.prompt.supervisor import SupervisorPrompt

__all__ = [
    "SYSTEM_PROMPT",
    "NEXT_STEP_PROMPT",
    "TOOLCALL_SYSTEM_PROMPT",
    "SupervisorPrompt",
]
