"""
anthropic_adapter.py — Anthropic API streaming adapter.

Implements direct SSE streaming against the Anthropic Messages API
(https://api.anthropic.com/v1/messages) using httpx.AsyncClient without
depending on the anthropic SDK.

Supported API version: 2023-06-01
Tested against: claude-3-5-sonnet-20241022, claude-3-7-sonnet-20250219
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

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

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, read=300.0)
_MAX_RETRIES = 3


class AnthropicAdapter(BaseLLMAdapter):
    """
    Adapter for the Anthropic Messages API with SSE streaming.

    Uses httpx.AsyncClient for all HTTP communication and manually parses the
    server-sent event stream. Handles rate-limit retries via the retry-after
    header and maps all Anthropic SSE event types to the shared LLMEvent types.

    Args:
        model: Anthropic model identifier (e.g. "claude-3-5-sonnet-20241022").
        api_key: Anthropic API key (x-api-key header).
        timeout: Optional httpx.Timeout override.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
            "accept": "text/event-stream",
        }

    def _build_payload(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> dict:
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]
        return payload

    async def stream(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> AsyncIterator[LLMEvent]:
        """
        Stream events from the Anthropic Messages API.

        Parses the SSE stream and yields typed LLMEvent objects.
        Handles rate limits with exponential back-off using retry-after.
        """
        payload = self._build_payload(messages, tools, system, max_tokens)
        headers = self._build_headers()

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        _API_URL,
                        json=payload,
                        headers=headers,
                    ) as response:
                        if response.status_code == 429:
                            retry_after = float(
                                response.headers.get("retry-after", 5 * (attempt + 1))
                            )
                            logger.warning(
                                "Rate limited by Anthropic API; retrying in %.1fs",
                                retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        if response.status_code != 200:
                            body = await response.aread()
                            yield ErrorEvent(
                                message=(
                                    f"Anthropic API error {response.status_code}: "
                                    f"{body.decode(errors='replace')}"
                                )
                            )
                            return

                        async for event in self._parse_sse(response):
                            yield event
                        return  # success — exit retry loop

            except httpx.TimeoutException as exc:
                logger.warning("Request timed out (attempt %d): %s", attempt + 1, exc)
                if attempt == _MAX_RETRIES - 1:
                    yield ErrorEvent(message=f"Request timed out after {_MAX_RETRIES} attempts: {exc}")
            except httpx.RequestError as exc:
                logger.error("HTTP request error: %s", exc)
                yield ErrorEvent(message=f"Network error: {exc}")
                return

    async def _parse_sse(
        self, response: httpx.Response
    ) -> AsyncIterator[LLMEvent]:
        """
        Parse the raw SSE byte stream from Anthropic and yield LLMEvent objects.

        SSE format:
            event: <event_type>
            data: <json_payload>
            (blank line)

        Anthropic event types handled:
          - content_block_start   (text or tool_use block begins)
          - content_block_delta   (text_delta or input_json_delta)
          - content_block_stop    (block finished)
          - message_delta         (stop_reason + usage)
          - message_stop          (stream finished)
          - error                 (API error object)
        """
        event_type: str = ""
        # Per-block state keyed by block index
        tool_blocks: dict[int, dict] = {}  # index -> partial ToolUseEvent state
        current_index: int = -1

        async for line in response.aiter_lines():
            line = line.rstrip()

            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
                continue

            if line.startswith("data:"):
                raw = line[len("data:"):].strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    logger.warning("Failed to parse SSE data JSON: %s | raw=%r", exc, raw)
                    continue

                async for ev in self._handle_sse_event(
                    event_type, data, tool_blocks, current_index
                ):
                    if isinstance(ev, _IndexUpdate):
                        current_index = ev.index
                    else:
                        yield ev
                continue

            # Blank line resets event type
            if line == "":
                event_type = ""

    async def _handle_sse_event(
        self,
        event_type: str,
        data: dict,
        tool_blocks: dict[int, dict],
        current_index: int,
    ) -> AsyncIterator[LLMEvent | "_IndexUpdate"]:
        """Dispatch a single parsed SSE event."""

        if event_type == "error":
            err = data.get("error", {})
            yield ErrorEvent(
                message=f"{err.get('type', 'error')}: {err.get('message', str(data))}"
            )
            return

        if event_type == "content_block_start":
            index: int = data.get("index", 0)
            yield _IndexUpdate(index)
            block = data.get("content_block", {})
            block_type = block.get("type", "")

            if block_type == "text":
                pass  # text blocks start empty; deltas carry the text

            elif block_type == "tool_use":
                tool_blocks[index] = {
                    "tool_use_id": block.get("id", ""),
                    "tool_name": block.get("name", ""),
                    "input_json": "",
                }
                yield ToolUseEvent(
                    type=EventType.TOOL_USE_START,
                    tool_use_id=block.get("id", ""),
                    tool_name=block.get("name", ""),
                    input={},
                )
            return

        if event_type == "content_block_delta":
            index = data.get("index", current_index)
            delta = data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                yield TextDeltaEvent(text=delta.get("text", ""))

            elif delta_type == "input_json_delta":
                partial = delta.get("partial_json", "")
                if index in tool_blocks:
                    tool_blocks[index]["input_json"] += partial
                yield ToolUseEvent(
                    type=EventType.TOOL_USE_INPUT_DELTA,
                    tool_use_id=tool_blocks.get(index, {}).get("tool_use_id", ""),
                    tool_name=tool_blocks.get(index, {}).get("tool_name", ""),
                    input={},
                )
            return

        if event_type == "content_block_stop":
            index = data.get("index", current_index)
            if index in tool_blocks:
                tb = tool_blocks.pop(index)
                try:
                    parsed_input = json.loads(tb["input_json"]) if tb["input_json"] else {}
                except json.JSONDecodeError:
                    parsed_input = {}
                yield ToolUseEvent(
                    type=EventType.TOOL_USE_DONE,
                    tool_use_id=tb["tool_use_id"],
                    tool_name=tb["tool_name"],
                    input=parsed_input,
                )
            else:
                yield TextDeltaEvent(type=EventType.TEXT_DONE, text="")
            return

        if event_type == "message_delta":
            delta = data.get("delta", {})
            usage = data.get("usage", {})
            yield MessageDoneEvent(
                stop_reason=delta.get("stop_reason", ""),
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )
            return

        if event_type == "message_stop":
            # Final sentinel; MessageDoneEvent was already emitted in message_delta
            return

    def format_tool_result(
        self,
        tool_use_id: str,
        content: str,
        is_error: bool = False,
    ) -> dict:
        """
        Format a tool result as an Anthropic tool_result content block.

        Returns:
            Dict conforming to Anthropic's tool_result content block schema.
        """
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
            "is_error": is_error,
        }


class _IndexUpdate:
    """Internal sentinel to propagate block index updates through the generator."""

    __slots__ = ("index",)

    def __init__(self, index: int) -> None:
        self.index = index
