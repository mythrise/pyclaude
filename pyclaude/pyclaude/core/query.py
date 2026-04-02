"""Top-level query runner."""

from __future__ import annotations

from pyclaude.constants import COMPACT_THRESHOLD

from .engine import ConversationEngine


async def run_query(
    user_input: str,
    engine: ConversationEngine,
    on_text=None,
    on_tool_start=None,
    on_tool_done=None,
) -> str:
    if engine.history.token_count() > COMPACT_THRESHOLD:
        raise RuntimeError("Conversation context is too large. Compact the session before continuing.")
    try:
        return await engine.chat(
            user_input,
            on_text=on_text,
            on_tool_start=on_tool_start,
            on_tool_done=on_tool_done,
        )
    except Exception as exc:
        raise RuntimeError(f"Query failed: {exc}") from exc
