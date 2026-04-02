"""autoDream background task implementations."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from pyclaude.core import ConversationEngine


@dataclass
class DreamResult:
    task_name: str
    success: bool
    summary: str
    details: str
    duration: float


class DreamTask(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, engine: ConversationEngine, cwd: str) -> DreamResult:
        raise NotImplementedError


class TodoScannerTask(DreamTask):
    name = "todo_scanner"
    description = "Scan the repo for TODO and FIXME markers."

    async def run(self, engine: ConversationEngine, cwd: str) -> DreamResult:
        started = time.perf_counter()
        matches: list[str] = []
        for path in Path(cwd).rglob("*"):
            if path.is_file():
                try:
                    for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                        if "TODO" in line or "FIXME" in line:
                            matches.append(f"{path}:{index}:{line.strip()}")
                except OSError:
                    continue
        details = "\n".join(matches[:100]) or "No TODO/FIXME found."
        return DreamResult(self.name, True, "Scanned for TODOs", details, time.perf_counter() - started)


class CodeReviewerTask(DreamTask):
    name = "code_reviewer"
    description = "Ask the LLM for a brief code health observation."

    async def run(self, engine: ConversationEngine, cwd: str) -> DreamResult:
        started = time.perf_counter()
        prompt = f"Give one concise code-health observation for the repository at {cwd}."
        summary = await engine.chat(prompt)
        return DreamResult(self.name, True, "Generated code review note", summary, time.perf_counter() - started)


class DocUpdaterTask(DreamTask):
    name = "doc_updater"
    description = "Check whether README exists and summarize documentation gaps."

    async def run(self, engine: ConversationEngine, cwd: str) -> DreamResult:
        started = time.perf_counter()
        readme = Path(cwd) / "README.md"
        details = "README.md exists." if readme.exists() else "README.md is missing."
        await asyncio.sleep(0)
        return DreamResult(self.name, True, "Checked docs", details, time.perf_counter() - started)
