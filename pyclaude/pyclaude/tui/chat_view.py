"""Rich chat transcript widgets."""

from __future__ import annotations

import re
from typing import Any

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.containers import ScrollableContainer
from textual.widgets import Static

from .tool_output import format_diff, truncate_output

_FENCED_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


def _render_markdown(text: str) -> RenderableType:
    if not text.strip():
        return Text("")

    parts: list[RenderableType] = []
    cursor = 0
    for match in _FENCED_BLOCK_RE.finditer(text):
        start, end = match.span()
        if start > cursor:
            prose = text[cursor:start].strip("\n")
            if prose:
                parts.append(Markdown(prose))
        language = match.group(1).strip() or "text"
        code = match.group(2).rstrip("\n")
        parts.append(Syntax(code, language, theme="github-dark", line_numbers=False, word_wrap=True))
        cursor = end
    if cursor < len(text):
        tail = text[cursor:].strip("\n")
        if tail:
            parts.append(Markdown(tail))
    if not parts:
        return Markdown(text)
    return Group(*parts)


def _tool_panel(title: str, body: RenderableType, border_style: str) -> Panel:
    return Panel(body, title=title, border_style=border_style, padding=(0, 1))


class MessageWidget(Static):
    def __init__(self, role: str, text: str = "", meta: dict[str, Any] | None = None) -> None:
        classes = f"message {role}"
        super().__init__("", classes=classes)
        self.role = role
        self.meta = meta or {}
        self._buffer = text
        self.update_renderable()

    def append(self, text: str) -> None:
        self._buffer += text
        self.update_renderable()

    def set_text(self, text: str) -> None:
        self._buffer = text
        self.update_renderable()

    def update_renderable(self) -> None:
        self.update(self._build_renderable())

    def _build_renderable(self) -> RenderableType:
        if self.role == "user":
            line = self._buffer.rstrip() or ""
            prefixed = "\n".join(f"> {part}" for part in line.splitlines()) if line else "> "
            return Text(prefixed, style="#58a6ff")
        if self.role == "assistant":
            return _render_markdown(self._buffer)
        if self.role == "tool":
            header = self.meta.get("header", "⟳ Tool")
            return _tool_panel(header, Text(self._buffer), "#238636")
        if self.role == "tool-result":
            title = self.meta.get("title", "Result")
            body_text = self._buffer
            if body_text.lstrip().startswith(("diff ", "---", "@@")):
                body: RenderableType = format_diff(body_text)
            else:
                clipped, truncated = truncate_output(body_text, max_lines=10)
                if truncated:
                    clipped = f"{clipped}\n\n… output collapsed …"
                body = Text(clipped, style="#9da7b3")
            return _tool_panel(title, body, "#6e7681")
        if self.role == "error":
            return _tool_panel("Error", Text(self._buffer, style="#ff7b72"), "#da3633")
        return Text(self._buffer)


class ChatView(ScrollableContainer):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._assistant_widget: MessageWidget | None = None

    def add_user_message(self, text: str) -> None:
        self._assistant_widget = None
        self.mount(MessageWidget("user", text))
        self._scroll_to_bottom()

    def add_assistant_start(self) -> None:
        self._assistant_widget = MessageWidget("assistant", "")
        self.mount(self._assistant_widget)
        self._scroll_to_bottom()

    def add_assistant_chunk(self, text: str) -> None:
        if self._assistant_widget is None:
            self.add_assistant_start()
        assert self._assistant_widget is not None
        self._assistant_widget.append(text)
        self._scroll_to_bottom()

    def add_assistant_end(self) -> None:
        self._assistant_widget = None
        self._scroll_to_bottom()

    def add_tool_start(self, name: str, args_summary: str) -> None:
        self._assistant_widget = None
        header = f"⟳ {name}  {args_summary}".strip()
        self.mount(MessageWidget("tool", args_summary, meta={"header": header}))
        self._scroll_to_bottom()

    def add_tool_result(self, output: str, exit_code: int) -> None:
        self._assistant_widget = None
        title = f"Result  exit={exit_code}"
        self.mount(MessageWidget("tool-result", output, meta={"title": title}))
        self._scroll_to_bottom()

    def add_error(self, msg: str) -> None:
        self._assistant_widget = None
        self.mount(MessageWidget("error", msg))
        self._scroll_to_bottom()

    def clear(self) -> None:
        self._assistant_widget = None
        for child in list(self.children):
            child.remove()

    def _scroll_to_bottom(self) -> None:
        self.call_after_refresh(self.scroll_end, animate=False)
