"""Filesystem glob tool."""

from __future__ import annotations

from pathlib import Path

from .base import BaseTool, ToolResult


class GlobTool(BaseTool):
    name = "glob"
    description = "Find files using a glob pattern."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["pattern"],
    }

    async def run(self, input: dict) -> ToolResult:
        root = Path(str(input.get("path", "."))).expanduser()
        pattern = str(input.get("pattern", "*"))
        matches = sorted(root.rglob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        text = "\n".join(str(match) for match in matches if match.exists())
        return ToolResult(content=[{"type": "text", "text": text}])
