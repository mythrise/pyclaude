"""Conversation history models."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from pyclaude.adapters.base import Message


class SessionMessage(BaseModel):
    role: str
    content: list[dict]
    timestamp: str = Field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    tokens_used: int = 0


class SessionHistory(BaseModel):
    messages: list[SessionMessage] = Field(default_factory=list)
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = Field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    total_tokens: int = 0

    def add_user(self, text: str) -> None:
        self.messages.append(SessionMessage(role="user", content=[{"type": "text", "text": text}]))

    def add_assistant(self, text: str, tokens_used: int = 0, content: list[dict] | None = None) -> None:
        payload = content if content is not None else [{"type": "text", "text": text}]
        self.messages.append(SessionMessage(role="assistant", content=payload, tokens_used=tokens_used))
        self.total_tokens += tokens_used

    def add_tool_result(self, content: list[dict], tokens_used: int = 0) -> None:
        self.messages.append(SessionMessage(role="user", content=content, tokens_used=tokens_used))
        self.total_tokens += tokens_used

    def to_messages(self) -> list[Message]:
        return [Message(role=item.role, content=item.content) for item in self.messages]

    def token_count(self) -> int:
        approximate = sum(len(str(block)) for msg in self.messages for block in msg.content) // 4
        return max(self.total_tokens, approximate)
