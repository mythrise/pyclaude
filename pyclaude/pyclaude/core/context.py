"""System prompt construction."""

from __future__ import annotations

import datetime as dt
import platform

from pyclaude.constants import DEFAULT_SYSTEM_PROMPT


def build_system_prompt(cwd: str) -> str:
    return DEFAULT_SYSTEM_PROMPT.format(
        cwd=cwd,
        platform=platform.platform(),
        datetime=dt.datetime.now().isoformat(timespec="seconds"),
    )
