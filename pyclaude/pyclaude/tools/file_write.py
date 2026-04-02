"""Atomic file write tool."""

from __future__ import annotations

from pathlib import Path

from .base import BaseTool, ToolResult


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Write text to a file atomically."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    async def run(self, input: dict) -> ToolResult:
        path = Path(str(input.get("path", ""))).expanduser()
        content = str(input.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
        return ToolResult(content=[{"type": "text", "text": f"Wrote {len(content)} bytes to {path}"}])
