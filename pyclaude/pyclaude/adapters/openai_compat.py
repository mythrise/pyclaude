"""OpenAI-compatible chat completions adapter."""

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


class OpenAICompatAdapter(BaseLLMAdapter):
    """Adapter for OpenAI-compatible `/v1/chat/completions` APIs."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "",
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "dummy"
        self.timeout = timeout or httpx.Timeout(30.0, read=300.0)

    def _build_headers(self) -> dict[str, str]:
        return {
            "accept": "text/event-stream",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}",
        }

    def _build_messages(self, messages: list[Message], system: str) -> list[dict[str, Any]]:
        built: list[dict[str, Any]] = []
        if system:
            built.append({"role": "system", "content": system})
        for message in messages:
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in message.content:
                block_type = block.get("type")
                if block_type == "text":
                    text_parts.append(str(block.get("text", "")))
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
            if text_parts or tool_calls:
                item: dict[str, Any] = {
                    "role": message.role,
                    "content": "\n".join(part for part in text_parts if part) or None,
                }
                if tool_calls:
                    item["tool_calls"] = tool_calls
                built.append(item)
        return built

    async def stream(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> AsyncIterator[LLMEvent]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(messages, system),
            "stream": True,
            "max_tokens": max_tokens,
        }
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._build_headers(),
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        yield ErrorEvent(
                            message=(
                                f"OpenAI-compatible API error {response.status_code}: "
                                f"{body.decode(errors='replace')}"
                            )
                        )
                        return
                    async for event in self._parse_sse(response):
                        yield event
        except httpx.ConnectError as exc:
            yield ErrorEvent(message=f"无法连接到 OpenAI 兼容接口 {self.base_url}: {exc}")
        except httpx.RequestError as exc:
            yield ErrorEvent(message=f"OpenAI 兼容接口请求失败: {exc}")

    async def _parse_sse(self, response: httpx.Response) -> AsyncIterator[LLMEvent]:
        tool_state: dict[str, dict[str, Any]] = {}
        async for line in response.aiter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices", [])
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta", {})
            if delta.get("content"):
                yield TextDeltaEvent(text=str(delta["content"]))

            for call in delta.get("tool_calls", []):
                index = str(call.get("index", 0))
                function = call.get("function", {})
                state = tool_state.setdefault(
                    index,
                    {
                        "id": call.get("id") or f"tool-{index}",
                        "name": function.get("name", ""),
                        "arguments": "",
                        "started": False,
                    },
                )
                if function.get("name"):
                    state["name"] = function["name"]
                if call.get("id"):
                    state["id"] = call["id"]
                if not state["started"]:
                    state["started"] = True
                    yield ToolUseEvent(
                        type=EventType.TOOL_USE_START,
                        tool_use_id=str(state["id"]),
                        tool_name=str(state["name"]),
                        input={},
                    )
                state["arguments"] += str(function.get("arguments", ""))
                yield ToolUseEvent(
                    type=EventType.TOOL_USE_INPUT_DELTA,
                    tool_use_id=str(state["id"]),
                    tool_name=str(state["name"]),
                    input={},
                )

            finish_reason = choice.get("finish_reason")
            if finish_reason == "tool_calls":
                for state in tool_state.values():
                    try:
                        parsed = json.loads(state["arguments"]) if state["arguments"] else {}
                    except json.JSONDecodeError:
                        parsed = {}
                    yield ToolUseEvent(
                        type=EventType.TOOL_USE_DONE,
                        tool_use_id=str(state["id"]),
                        tool_name=str(state["name"]),
                        input=parsed if isinstance(parsed, dict) else {},
                    )
                usage = data.get("usage", {})
                yield MessageDoneEvent(
                    stop_reason="tool_use",
                    input_tokens=int(usage.get("prompt_tokens", 0)),
                    output_tokens=int(usage.get("completion_tokens", 0)),
                )
                tool_state.clear()
            elif finish_reason:
                usage = data.get("usage", {})
                yield MessageDoneEvent(
                    stop_reason=str(finish_reason),
                    input_tokens=int(usage.get("prompt_tokens", 0)),
                    output_tokens=int(usage.get("completion_tokens", 0)),
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
