"""Formatting for autoDream results."""

from __future__ import annotations

from .tasks import DreamResult


def format_dream_result(result: DreamResult) -> str:
    status = "Success" if result.success else "Failed"
    return (
        f"## autoDream: {result.task_name}\n\n"
        f"- Status: {status}\n"
        f"- Summary: {result.summary}\n"
        f"- Duration: {result.duration:.2f}s\n\n"
        f"{result.details}"
    )


def format_dream_notification(result: DreamResult) -> str:
    return f"{result.task_name}: {result.summary}"[:30]
