"""Precise string replacement tool."""

from __future__ import annotations

import difflib
from pathlib import Path

from .base import BaseTool, ToolResult


class FileEditTool(BaseTool):
    name = "file_edit"
    description = "Apply an exact string replacement to a file."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
            "replace_all": {"type": "boolean"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def run(self, input: dict) -> ToolResult:
        path = Path(str(input.get("path", ""))).expanduser()
        if not path.exists():
            return ToolResult(content=[{"type": "text", "text": f"File not found: {path}"}], is_error=True)
        old = str(input.get("old_string", ""))
        new = str(input.get("new_string", ""))
        replace_all = bool(input.get("replace_all", False))
        original = path.read_text(encoding="utf-8", errors="replace")
        occurrences = original.count(old)
        if occurrences == 0:
            return ToolResult(content=[{"type": "text", "text": "old_string not found"}], is_error=True)
        if not replace_all and occurrences != 1:
            return ToolResult(
                content=[{"type": "text", "text": f"old_string matched {occurrences} times"}],
                is_error=True,
            )
        updated = original.replace(old, new) if replace_all else original.replace(old, new, 1)
        path.write_text(updated, encoding="utf-8")
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
            )
        )
        return ToolResult(content=[{"type": "text", "text": diff}])
