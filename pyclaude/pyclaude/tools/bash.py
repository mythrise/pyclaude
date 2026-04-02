"""Shell execution tool."""

from __future__ import annotations

import asyncio
import re

from pyclaude.constants import TOOL_TIMEOUT

from .base import BaseTool, ToolResult

_OUTPUT_LIMIT = 50 * 1024
_DANGEROUS_PATTERNS = (
    re.compile(r"rm\s+-rf\s+/$"),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"),
    re.compile(r"dd\s+if=/dev/"),
)


class BashTool(BaseTool):
    name = "bash"
    description = "Run a shell command in the current working directory."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "minimum": 1, "maximum": TOOL_TIMEOUT},
        },
        "required": ["command"],
    }

    async def run(self, input: dict) -> ToolResult:
        command = str(input.get("command", "")).strip()
        if not command:
            return ToolResult(content=[{"type": "text", "text": "Missing command"}], is_error=True)
        if self._is_dangerous(command):
            return ToolResult(
                content=[{"type": "text", "text": f"Blocked dangerous command: {command}"}],
                is_error=True,
            )
        timeout = min(int(input.get("timeout", TOOL_TIMEOUT)), TOOL_TIMEOUT)
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return ToolResult(
                content=[{"type": "text", "text": f"Command timed out after {timeout}s"}],
                is_error=True,
            )

        payload = {
            "stdout": self._truncate(stdout.decode(errors="replace")),
            "stderr": self._truncate(stderr.decode(errors="replace")),
            "exit_code": proc.returncode,
        }
        return ToolResult(content=[{"type": "text", "text": str(payload)}], is_error=proc.returncode != 0)

    def _truncate(self, text: str) -> str:
        encoded = text.encode()
        if len(encoded) <= _OUTPUT_LIMIT:
            return text
        clipped = encoded[:_OUTPUT_LIMIT].decode(errors="replace")
        return f"{clipped}\n...[truncated]..."

    def _is_dangerous(self, command: str) -> bool:
        normalized = " ".join(command.split())
        return any(pattern.search(normalized) for pattern in _DANGEROUS_PATTERNS)
