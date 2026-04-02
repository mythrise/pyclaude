"""Permission checker."""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from typing import Any

from .modes import PermissionMode, ToolCategory

AskCallback = Callable[[str, dict[str, Any], ToolCategory], bool | Awaitable[bool]]


class PermissionChecker:
    def __init__(self, mode: PermissionMode | str, ask_callback: AskCallback | None = None) -> None:
        self.mode = PermissionMode(mode)
        self.ask_callback = ask_callback

    async def check(self, tool_name: str, tool_input: dict, category: ToolCategory) -> bool:
        if self.mode == PermissionMode.BYPASS:
            return True
        if self.mode == PermissionMode.PLAN:
            return category == ToolCategory.READ_ONLY
        if self.mode == PermissionMode.AUTO:
            return True
        if category == ToolCategory.DESTRUCTIVE:
            return False
        if category == ToolCategory.BASH and self._is_destructive_bash(str(tool_input.get("command", ""))):
            return False
        if self.ask_callback is None:
            return category == ToolCategory.READ_ONLY
        result = self.ask_callback(tool_name, tool_input, category)
        if inspect.isawaitable(result):
            return bool(await result)
        return bool(result)

    def _is_destructive_bash(self, command: str) -> bool:
        normalized = " ".join(command.split())
        patterns = (
            r"rm\s+-rf\s+/",
            r":\(\)\s*\{\s*:\|:&\s*\};:",
            r"dd\s+if=/dev/",
            r"mkfs",
            r">\s*/dev/sd",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)
