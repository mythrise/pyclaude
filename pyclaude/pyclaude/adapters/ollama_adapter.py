"""Ollama chat adapter with NDJSON streaming support."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .base import (
    BaseLLMAdapter,
    ErrorEvent,
    EventType,
    LLMEvent,
    Message,
    MessageDoneEvent,
    TextDeltaEvent,
    Tool,
    ToolUseEvent,
)


class OllamaAdapter(BaseLLMAdapter):
    """Adapter for the local Ollama `/api/chat` endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or httpx.Timeout(30.0, read=300.0)

    def _build_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        built: list[dict[str, Any]] = []
        for message in messages:
            content_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in message.content:
                block_type = block.get("type")
                if block_type == "text":
                    content_parts.append(str(block.get("text", "")))
                elif block_type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(block.get("input", {})),
                            },
                        }
                    )
                elif block_type == "tool_result":
                    built.append(
                        {
                            "role": "tool",
                            "content": block.get("content", ""),
                            "tool_call_id": block.get("tool_use_id", ""),
                        }
                    )
            if content_parts or tool_calls:
                item: dict[str, Any] = {
                    "role": message.role,
                    "content": "\n".join(part for part in content_parts if part),
                }
                if tool_calls:
                    item["tool_calls"] = tool_calls
                built.append(item)
        return built

    def _build_payload(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "messages": self._build_messages(messages),
            "options": {"num_predict": max_tokens},
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}, *payload["messages"]]
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in tools
            ]
        return payload

    async def stream(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> AsyncIterator[LLMEvent]:
        payload = self._build_payload(messages, tools, system, max_tokens)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        yield ErrorEvent(
                            message=(
                                f"Ollama API error {response.status_code}: "
                                f"{body.decode(errors='replace')}"
                            )
                        )
                        return

                    async for event in self._parse_ndjson(response):
                        yield event
        except httpx.ConnectError as exc:
            yield ErrorEvent(
                message=(
                    f"无法连接到 Ollama ({self.base_url})。"
                    "请确认 Ollama 已启动，并且模型已可用。"
                    f" 原始错误: {exc}"
                )
            )
        except httpx.RequestError as exc:
            yield ErrorEvent(message=f"Ollama 请求失败: {exc}")

    async def _parse_ndjson(self, response: httpx.Response) -> AsyncIterator[LLMEvent]:
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if "error" in data:
                yield ErrorEvent(message=str(data["error"]))
                return

            message = data.get("message", {})
            content = message.get("content")
            if content:
                yield TextDeltaEvent(text=str(content))

            for tool_call in message.get("tool_calls", []):
                function = tool_call.get("function", {})
                raw_args = function.get("arguments", {})
                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        parsed_args = {}
                else:
                    parsed_args = raw_args
                tool_id = str(tool_call.get("id") or function.get("name") or "tool-call")
                yield ToolUseEvent(
                    type=EventType.TOOL_USE_START,
                    tool_use_id=tool_id,
                    tool_name=str(function.get("name", "")),
                    input={},
                )
                yield ToolUseEvent(
                    type=EventType.TOOL_USE_DONE,
                    tool_use_id=tool_id,
                    tool_name=str(function.get("name", "")),
                    input=parsed_args if isinstance(parsed_args, dict) else {},
                )

            if data.get("done"):
                prompt_eval = data.get("prompt_eval_count", 0)
                eval_count = data.get("eval_count", 0)
                yield MessageDoneEvent(
                    stop_reason="tool_use" if message.get("tool_calls") else "end_turn",
                    input_tokens=int(prompt_eval or 0),
                    output_tokens=int(eval_count or 0),
                )

    def format_tool_result(
        self,
        tool_use_id: str,
        content: str,
        is_error: bool = False,
    ) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
            "is_error": is_error,
        }
