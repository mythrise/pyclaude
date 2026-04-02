import asyncio
from collections.abc import AsyncIterator

from pyclaude.adapters.base import (
    BaseLLMAdapter,
    EventType,
    Message,
    MessageDoneEvent,
    TextDeltaEvent,
    Tool,
    ToolUseEvent,
)
from pyclaude.core import ConversationEngine, SessionHistory
from pyclaude.permissions import PermissionChecker, PermissionMode
from pyclaude.tools import BaseTool, ToolRegistry, ToolResult


class EchoTool(BaseTool):
    name = "echo"
    description = "echo"
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def run(self, input: dict) -> ToolResult:
        return ToolResult(content=[{"type": "text", "text": input["text"]}])


class MockAdapter(BaseLLMAdapter):
    def __init__(self) -> None:
        self.calls = 0

    async def stream(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> AsyncIterator:
        self.calls += 1
        if self.calls == 1:
            yield ToolUseEvent(
                type=EventType.TOOL_USE_DONE,
                tool_use_id="1",
                tool_name="echo",
                input={"text": "from tool"},
            )
            yield MessageDoneEvent(stop_reason="tool_use")
        else:
            yield TextDeltaEvent(text="done")
            yield MessageDoneEvent(stop_reason="end_turn", output_tokens=3)

    def format_tool_result(self, tool_use_id: str, content: str, is_error: bool = False) -> dict:
        return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content, "is_error": is_error}


def test_engine_tool_loop() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    engine = ConversationEngine(
        adapter=MockAdapter(),
        tool_registry=registry,
        permission_checker=PermissionChecker(PermissionMode.AUTO),
        history=SessionHistory(),
    )
    result = asyncio.run(engine.chat("hi"))
    assert result == "done"
    assert len(engine.history.messages) >= 3
