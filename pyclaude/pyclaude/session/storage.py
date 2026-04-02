"""Session persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pyclaude.config import SESSIONS_DIR
from pyclaude.core.history import SessionHistory


@dataclass
class SessionMeta:
    session_id: str
    created_at: str
    message_count: int
    first_message: str
    total_tokens: int


class SessionStorage:
    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or SESSIONS_DIR
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, history: SessionHistory) -> Path:
        path = self.base_path / f"{history.session_id}.json"
        path.write_text(history.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, session_id: str) -> SessionHistory:
        path = self.base_path / f"{session_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionHistory.model_validate(data)

    def list_sessions(self) -> list[SessionMeta]:
        metas: list[SessionMeta] = []
        for path in sorted(self.base_path.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            history = SessionHistory.model_validate_json(path.read_text(encoding="utf-8"))
            first_message = ""
            if history.messages:
                first_message = str(history.messages[0].content[0].get("text", ""))[:80]
            metas.append(
                SessionMeta(
                    session_id=history.session_id,
                    created_at=history.created_at,
                    message_count=len(history.messages),
                    first_message=first_message,
                    total_tokens=history.total_tokens,
                )
            )
        return metas

    def delete(self, session_id: str) -> None:
        path = self.base_path / f"{session_id}.json"
        if path.exists():
            path.unlink()
