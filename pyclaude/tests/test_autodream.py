import asyncio

from pyclaude.autodream import DreamScheduler, IdleDetector
from pyclaude.config import AutoDreamConfig
from pyclaude.core import ConversationEngine, SessionHistory
from pyclaude.permissions import PermissionChecker, PermissionMode
from pyclaude.tools import ToolRegistry

from .test_engine import MockAdapter


def test_idle_detector() -> None:
    detector = IdleDetector(threshold=0)
    assert detector.is_idle()


def test_scheduler_runs_task() -> None:
    config = AutoDreamConfig(enabled=True, idle_threshold=0, tasks=["doc_updater"])
    results = []
    scheduler = DreamScheduler(
        config=config,
        engine=ConversationEngine(
            adapter=MockAdapter(),
            tool_registry=ToolRegistry(),
            permission_checker=PermissionChecker(PermissionMode.AUTO),
            history=SessionHistory(),
        ),
        on_dream_done=lambda result: results.append(result),
    )
    async def runner() -> None:
        await scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()

    asyncio.run(runner())
    assert results
