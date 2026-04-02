"""autoDream scheduler."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from pyclaude.config import AutoDreamConfig
from pyclaude.core import ConversationEngine
from pyclaude.utils.cwd import get_cwd

from .detector import IdleDetector
from .tasks import CodeReviewerTask, DocUpdaterTask, DreamResult, DreamTask, TodoScannerTask


class DreamScheduler:
    def __init__(
        self,
        config: AutoDreamConfig,
        engine: ConversationEngine,
        on_dream_start: Callable[[DreamTask], None] | None = None,
        on_dream_done: Callable[[DreamResult], None] | None = None,
    ) -> None:
        self.config = config
        self.engine = engine
        self.on_dream_start = on_dream_start
        self.on_dream_done = on_dream_done
        self.detector = IdleDetector(config.idle_threshold)
        self._task: asyncio.Task | None = None
        self._paused = False
        self._running = False
        self._tasks = {
            "todo_scanner": TodoScannerTask(),
            "code_reviewer": CodeReviewerTask(),
            "doc_updater": DocUpdaterTask(),
        }

    async def start(self) -> None:
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def pause(self) -> None:
        self._paused = True

    async def resume(self) -> None:
        self._paused = False
        self.detector.on_user_activity()

    async def _scheduler_loop(self) -> None:
        while self._running:
            if self._paused or not self.config.enabled:
                await asyncio.sleep(1)
                continue
            await self.detector.wait_for_idle()
            if not self._running or self._paused:
                continue
            for task_name in self.config.tasks:
                task = self._tasks.get(task_name)
                if task is None:
                    continue
                if self.on_dream_start is not None:
                    self.on_dream_start(task)
                result = await task.run(self.engine, get_cwd())
                if self.on_dream_done is not None:
                    self.on_dream_done(result)
                self.detector.on_user_activity()
                break
