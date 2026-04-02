"""File read tool."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from .base import BaseTool, ToolResult

_MAX_SIZE = 10 * 1024 * 1024
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Read a file from disk, optionally with offset and limit."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1},
        },
        "required": ["path"],
    }

    async def run(self, input: dict) -> ToolResult:
        path = Path(str(input.get("path", ""))).expanduser()
        if not path.exists():
            return ToolResult(content=[{"type": "text", "text": f"File not found: {path}"}], is_error=True)
        if path.stat().st_size > _MAX_SIZE:
            return ToolResult(content=[{"type": "text", "text": f"File too large: {path}"}], is_error=True)
        if path.suffix.lower() in _IMAGE_EXTENSIONS:
            media_type = mimetypes.guess_type(path.name)[0] or "image/png"
            data = base64.b64encode(path.read_bytes()).decode()
            return ToolResult(
                content=[
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": data,
                        },
                    }
                ]
            )
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        offset = max(0, int(input.get("offset", 0)))
        limit = int(input["limit"]) if input.get("limit") is not None else None
        selected = lines[offset:] if limit is None else lines[offset : offset + limit]
        numbered = "\n".join(f"{idx:>6}\t{line}" for idx, line in enumerate(selected, start=offset + 1))
        return ToolResult(content=[{"type": "text", "text": numbered}])
