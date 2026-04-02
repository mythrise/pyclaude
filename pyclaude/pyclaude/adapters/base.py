"""
base.py — Abstract base class and shared data types for LLM adapters.

All adapters must subclass BaseLLMAdapter and implement the stream() and
format_tool_result() methods using the event types defined here.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator
from enum import Enum


class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TEXT_DONE = "text_done"
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_INPUT_DELTA = "tool_use_input_delta"
    TOOL_USE_DONE = "tool_use_done"
    MESSAGE_DONE = "message_done"
    ERROR = "error"


@dataclass
class TextDeltaEvent:
    type: EventType = EventType.TEXT_DELTA
    text: str = ""


@dataclass
class ToolUseEvent:
    type: EventType = EventType.TOOL_USE_START
    tool_use_id: str = ""
    tool_name: str = ""
    input: dict = field(default_factory=dict)  # populated when DONE


@dataclass
class MessageDoneEvent:
    type: EventType = EventType.MESSAGE_DONE
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ErrorEvent:
    type: EventType = EventType.ERROR
    message: str = ""


LLMEvent = TextDeltaEvent | ToolUseEvent | MessageDoneEvent | ErrorEvent


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: list[dict]  # Anthropic-style content blocks


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict  # JSON Schema


class BaseLLMAdapter(ABC):
    """
    Abstract base for all LLM backend adapters.

    Subclasses must implement:
      - stream(): yield LLMEvent objects from a streaming API call
      - format_tool_result(): format a tool result into a message content block
    """

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
        max_tokens: int,
    ) -> AsyncIterator[LLMEvent]:
        """
        Stream events from the LLM backend.

        Args:
            messages: Conversation history in Anthropic content-block format.
            tools: List of tools available to the model.
            system: System prompt string.
            max_tokens: Maximum tokens to generate.

        Yields:
            LLMEvent instances (TextDeltaEvent, ToolUseEvent, MessageDoneEvent,
            or ErrorEvent).
        """
        ...

    @abstractmethod
    def format_tool_result(
        self,
        tool_use_id: str,
        content: str,
        is_error: bool = False,
    ) -> dict:
        """
        Format a tool result into an Anthropic-style content block dict.

        Args:
            tool_use_id: The ID of the originating tool_use block.
            content: String output from the tool execution.
            is_error: Whether the tool returned an error.

        Returns:
            A dict representing a tool_result content block.
        """
        ...
