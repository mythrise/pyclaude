"""Helpers for formatting tool arguments and output."""

from __future__ import annotations

from rich.text import Text


def format_diff(diff_text: str) -> Text:
    """Render a unified diff with line-level colors."""
    formatted = Text()
    for line in diff_text.splitlines():
        style = "dim"
        if line.startswith("@@"):
            style = "cyan"
        elif line.startswith("+") and not line.startswith("+++"):
            style = "green"
        elif line.startswith("-") and not line.startswith("---"):
            style = "red"
        elif line.startswith(("diff ", "index ", "---", "+++")):
            style = "bold"
        formatted.append(f"{line}\n", style=style)
    if not diff_text:
        formatted.append("(empty diff)", style="dim")
    return formatted


def format_bash_output(stdout: str, stderr: str, exit_code: int) -> str:
    """Format shell output with a compact exit status badge."""
    badge = f"[exit {exit_code}]"
    sections = [badge]
    if stdout.strip():
        sections.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        sections.append(f"stderr:\n{stderr.rstrip()}")
    if len(sections) == 1:
        sections.append("(no output)")
    return "\n\n".join(sections)


def format_tool_args(tool_name: str, args: dict) -> str:
    """Produce a one-line summary for tool invocation headers."""
    _ = tool_name
    if not args:
        return "{}"

    parts: list[str] = []
    for key, value in args.items():
        rendered = str(value).replace("\n", "\\n")
        if len(rendered) > 48:
            rendered = f"{rendered[:45]}..."
        parts.append(f"{key}={rendered}")

    summary = ", ".join(parts)
    if len(summary) > 120:
        summary = f"{summary[:117]}..."
    return summary


def truncate_output(text: str, max_lines: int = 10) -> tuple[str, bool]:
    """Truncate multi-line tool output while preserving the original text shape."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text, False
    clipped = "\n".join(lines[:max_lines])
    return clipped, True
