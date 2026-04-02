"""Buddy notification queue."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class Notification:
    text: str
    duration: float = 3.0
    style: str = "white"


class NotificationQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Notification] = asyncio.Queue()

    async def push(self, notification: Notification) -> None:
        await self._queue.put(notification)

    async def next(self) -> Notification:
        return await self._queue.get()

    async def notify_tool_done(self, tool_name: str) -> None:
        await self.push(Notification(text=f"{tool_name} 完成", style="green"))

    async def notify_error(self, text: str) -> None:
        await self.push(Notification(text=text[:30], style="red"))

    async def notify_dream_done(self, text: str) -> None:
        await self.push(Notification(text=text[:30], style="cyan"))
