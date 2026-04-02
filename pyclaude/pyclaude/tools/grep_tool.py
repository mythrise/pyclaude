"""Text search tool with ripgrep fast path."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from .base import BaseTool, ToolResult


class GrepTool(BaseTool):
    name = "grep"
    description = "Search files for a regex pattern."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
            "output_mode": {"type": "string", "enum": ["content", "files_with_matches", "count"]},
        },
        "required": ["pattern"],
    }

    async def run(self, input: dict) -> ToolResult:
        pattern = str(input.get("pattern", ""))
        root = Path(str(input.get("path", "."))).expanduser()
        output_mode = str(input.get("output_mode", "content"))
        rg_result = await self._run_rg(pattern, root, output_mode)
        if rg_result is not None:
            return ToolResult(content=[{"type": "text", "text": rg_result}])
        return ToolResult(content=[{"type": "text", "text": self._python_grep(pattern, root, output_mode)}])

    async def _run_rg(self, pattern: str, root: Path, output_mode: str) -> str | None:
        flags = ["rg", pattern, str(root)]
        if output_mode == "files_with_matches":
            flags.insert(1, "-l")
        elif output_mode == "count":
            flags.insert(1, "-c")
        else:
            flags.insert(1, "-n")
        try:
            proc = await asyncio.create_subprocess_exec(
                *flags,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return None
        stdout, stderr = await proc.communicate()
        if proc.returncode not in (0, 1):
            return stderr.decode(errors="replace")
        return stdout.decode(errors="replace")

    def _python_grep(self, pattern: str, root: Path, output_mode: str) -> str:
        regex = re.compile(pattern)
        matches: list[str] = []
        matched_files = 0
        total = 0
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            file_hit = False
            for index, line in enumerate(lines, start=1):
                if regex.search(line):
                    file_hit = True
                    total += 1
                    if output_mode == "content":
                        matches.append(f"{file_path}:{index}:{line}")
            if file_hit:
                matched_files += 1
                if output_mode == "files_with_matches":
                    matches.append(str(file_path))
        if output_mode == "count":
            return str(total if total else matched_files)
        return "\n".join(matches)
