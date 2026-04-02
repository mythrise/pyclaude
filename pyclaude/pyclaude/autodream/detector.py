"""Idle detection."""

from __future__ import annotations

import asyncio
import time


class IdleDetector:
    def __init__(self, threshold: int = 300) -> None:
        self.threshold = threshold
        self._last_activity = time.monotonic()

    def on_user_activity(self) -> None:
        self._last_activity = time.monotonic()

    def idle_seconds(self) -> float:
        return time.monotonic() - self._last_activity

    def is_idle(self) -> bool:
        return self.idle_seconds() >= self.threshold

    async def wait_for_idle(self) -> None:
        while not self.is_idle():
            await asyncio.sleep(min(1.0, max(0.1, self.threshold / 20)))
