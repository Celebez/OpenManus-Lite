"""View, create, and edit files (str_replace_editor)."""
from pathlib import Path

from app.config import config
from app.tool.base import BaseTool, ToolResult


class StrReplaceEditor(BaseTool):
    name: str = "str_replace_editor"
    description: str = (
        "Read, create, and edit files. Commands: view, create, str_replace, insert."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "enum": ["view", "create", "str_replace", "insert"]},
            "path": {"type": "string", "description": "Absolute or workspace-relative path."},
            "file_text": {"type": "string", "description": "Content for create."},
            "old_str": {"type": "string", "description": "String to replace (str_replace)."},
            "new_str": {"type": "string", "description": "Replacement string."},
            "insert_line": {"type": "integer", "description": "Line number for insert."},
        },
        "required": ["command", "path"],
    }

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = config.workspace_root / path
        return p

    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        path = kwargs.get("path")
        p = self._resolve(path)
        try:
            if command == "view":
                if not p.exists():
                    return self.fail_response(f"File not found: {p}")
                return self.success_response(p.read_text(errors="replace"))
            elif command == "create":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(kwargs.get("file_text", ""))
                return self.success_response(f"Created {p}")
            elif command == "str_replace":
                if not p.exists():
                    return self.fail_response(f"File not found: {p}")
                text = p.read_text()
                old = kwargs.get("old_str", "")
                new = kwargs.get("new_str", "")
                if old not in text:
                    return self.fail_response("old_str not found in file")
                p.write_text(text.replace(old, new, 1))
                return self.success_response(f"Replaced in {p}")
            elif command == "insert":
                text = p.read_text() if p.exists() else ""
                lines = text.splitlines()
                idx = kwargs.get("insert_line", 0)
                lines.insert(idx, kwargs.get("new_str", ""))
                p.write_text("\n".join(lines))
                return self.success_response(f"Inserted at line {idx} in {p}")
            return self.fail_response(f"Unknown command: {command}")
        except Exception as e:
            return self.fail_response(str(e))
