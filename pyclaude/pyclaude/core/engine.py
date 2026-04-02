"""Conversation engine with tool loop."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from pyclaude.adapters.base import BaseLLMAdapter, EventType, ToolUseEvent
from pyclaude.permissions import PermissionChecker, ToolCategory
from pyclaude.tools import ToolRegistry, ToolResult
from pyclaude.utils.cwd import get_cwd

from .context import build_system_prompt
from .history import SessionHistory

TextCallback = Callable[[str], Any]
ToolCallback = Callable[[str, dict], Any]
ToolDoneCallback = Callable[[str, ToolResult], Any]


class ConversationEngine:
    def __init__(
        self,
        adapter: BaseLLMAdapter,
        tool_registry: ToolRegistry,
        permission_checker: PermissionChecker,
        history: SessionHistory | None = None,
    ) -> None:
        self.adapter = adapter
        self.tool_registry = tool_registry
        self.permission_checker = permission_checker
        self.history = history or SessionHistory()

    async def chat(
        self,
        user_input: str,
        on_text: TextCallback | None = None,
        on_tool_start: ToolCallback | None = None,
        on_tool_done: ToolDoneCallback | None = None,
    ) -> str:
        self.history.add_user(user_input)
        final_text: list[str] = []
        while True:
            assistant_blocks: list[dict] = []
            pending_tools: list[ToolUseEvent] = []
            message_done_tokens = 0
            async for event in self.adapter.stream(
                messages=self.history.to_messages(),
                tools=self.tool_registry.to_anthropic_tools(),
                system=build_system_prompt(get_cwd()),
                max_tokens=8192,
            ):
                if event.type == EventType.TEXT_DELTA:
                    final_text.append(event.text)
                    assistant_blocks.append({"type": "text", "text": event.text})
                    if on_text is not None:
                        result = on_text(event.text)
                        if asyncio.iscoroutine(result):
                            await result
                elif event.type == EventType.TOOL_USE_DONE:
                    pending_tools.append(event)
                    assistant_blocks.append(
                        {
                            "type": "tool_use",
                            "id": event.tool_use_id,
                            "name": event.tool_name,
                            "input": event.input,
                        }
                    )
                    if on_tool_start is not None:
                        result = on_tool_start(event.tool_name, event.input)
                        if asyncio.iscoroutine(result):
                            await result
                elif event.type == EventType.MESSAGE_DONE:
                    message_done_tokens = event.input_tokens + event.output_tokens
                elif event.type == EventType.ERROR:
                    raise RuntimeError(event.message)

            if assistant_blocks:
                self.history.add_assistant("".join(final_text), tokens_used=message_done_tokens, content=assistant_blocks)

            if not pending_tools:
                return "".join(final_text).strip()

            tool_results = await asyncio.gather(*(self._execute_tool(tool_use) for tool_use in pending_tools))
            result_blocks: list[dict] = []
            for tool_use, result in zip(pending_tools, tool_results, strict=True):
                formatted = self.adapter.format_tool_result(tool_use.tool_use_id, result.as_text(), result.is_error)
                result_blocks.append(formatted)
                if on_tool_done is not None:
                    maybe = on_tool_done(tool_use.tool_name, result)
                    if asyncio.iscoroutine(maybe):
                        await maybe
            self.history.add_tool_result(result_blocks)
            final_text = []

    async def _execute_tool(self, tool_use: ToolUseEvent) -> ToolResult:
        tool = self.tool_registry.get(tool_use.tool_name)
        if tool is None:
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_use.tool_name}"}],
                is_error=True,
            )
        category = _tool_category(tool_use.tool_name, tool_use.input)
        allowed = await self.permission_checker.check(tool_use.tool_name, tool_use.input, category)
        if not allowed:
            return ToolResult(
                content=[{"type": "text", "text": f"Permission denied for tool: {tool_use.tool_name}"}],
                is_error=True,
            )
        return await tool.run(tool_use.input)


def _tool_category(tool_name: str, tool_input: dict) -> ToolCategory:
    if tool_name in {"file_read", "glob", "grep"}:
        return ToolCategory.READ_ONLY
    if tool_name == "web_fetch":
        return ToolCategory.NETWORK
    if tool_name == "bash":
        command = str(tool_input.get("command", ""))
        if any(token in command for token in ("rm -rf", "dd if=/dev/", "mkfs")):
            return ToolCategory.DESTRUCTIVE
        return ToolCategory.BASH
    return ToolCategory.FILE_WRITE
