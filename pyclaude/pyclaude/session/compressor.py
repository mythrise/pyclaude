"""History compression helpers."""

from __future__ import annotations

from pyclaude.adapters.base import BaseLLMAdapter
from pyclaude.core.history import SessionHistory
from pyclaude.tools import ToolRegistry


async def compress_history(
    history: SessionHistory,
    adapter: BaseLLMAdapter,
    keep_recent: int = 10,
) -> SessionHistory:
    if len(history.messages) <= keep_recent:
        return history
    old_messages = history.messages[:-keep_recent]
    recent_messages = history.messages[-keep_recent:]
    summary_prompt = "Summarize the following conversation for continued coding work."
    temp_history = SessionHistory(messages=old_messages)
    chunks: list[str] = []
    async for event in adapter.stream(
        messages=temp_history.to_messages(),
        tools=ToolRegistry().to_anthropic_tools(),
        system=summary_prompt,
        max_tokens=1024,
    ):
        if getattr(event, "text", ""):
            chunks.append(event.text)
    compressed = SessionHistory(session_id=history.session_id, created_at=history.created_at)
    compressed.add_assistant("".join(chunks).strip() or "Previous conversation summary.")
    compressed.messages.extend(recent_messages)
    compressed.total_tokens = history.total_tokens
    return compressed
