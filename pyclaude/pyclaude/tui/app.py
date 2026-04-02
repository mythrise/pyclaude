"""Main Textual application."""

from __future__ import annotations

import asyncio
import ast
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, TextArea

from pyclaude.adapters.factory import create_adapter
from pyclaude.buddy import BuddyWidget
from pyclaude.commands.builtin import register_builtins
from pyclaude.commands.registry import CommandRegistry
from pyclaude.config import Config
from pyclaude.core import ConversationEngine, SessionHistory
from pyclaude.permissions import PermissionChecker, PermissionMode, ToolCategory
from pyclaude.session.storage import SessionStorage
from pyclaude.tools import ToolRegistry, ToolResult

from .chat_view import ChatView
from .permission_dialog import PermissionDialog
from .theme import DARK_THEME
from .tool_output import format_bash_output, format_tool_args


class PyClaudeApp(App):
    CSS = DARK_THEME
    BINDINGS = [
        ("ctrl+j", "submit_prompt", "Submit"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("escape", "cancel_streaming", "Cancel"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.storage = SessionStorage()
        self.commands = CommandRegistry()
        self.permission_mode = PermissionMode(config.permissions.mode)
        self.permission_checker = PermissionChecker(self.permission_mode, self._ask_permission)
        self.engine = ConversationEngine(
            adapter=create_adapter(config),
            tool_registry=ToolRegistry.default(),
            permission_checker=self.permission_checker,
            history=SessionHistory(),
        )
        self.chat_view = ChatView(id="chat-view")
        self.header_bar = Static(id="header-bar")
        self.status_bar = Static(id="status-bar")
        self.composer = TextArea(id="composer")
        self.input_hint = Static("Ctrl+J 提交  /help 帮助  Ctrl+L 清屏  Ctrl+C 退出", id="input-hint")
        self.buddy = BuddyWidget() if config.buddy.enabled and BuddyWidget is not None else None
        self._stream_task: asyncio.Task[None] | None = None
        register_builtins(self.commands, self)
        self._set_status("Ready")

    def compose(self) -> ComposeResult:
        with Container(id="app-shell"):
            yield self.header_bar
            with Container(id="main-row"):
                yield self.chat_view
                if self.buddy is not None:
                    with Container(id="buddy-panel"):
                        yield self.buddy
            yield self.status_bar
            with Container(id="input-area"):
                yield self.composer
            yield self.input_hint

    def on_mount(self) -> None:
        self.composer.border_title = "Input"
        self.composer.focus()
        self._refresh_header()

    async def action_submit_prompt(self) -> None:
        text = self.composer.text.strip()
        if not text:
            return
        self.composer.load_text("")
        self.composer.focus()

        if text.startswith("/"):
            result = await self.commands.execute(text, self)
            self._sync_buddy_visibility()
            if result:
                self.chat_view.add_tool_result(str(result), 0)
                self._set_status("Command complete")
            self._refresh_header()
            return

        if self._stream_task is not None and not self._stream_task.done():
            self._set_status("Already streaming. Press Esc to cancel.")
            return

        self.chat_view.add_user_message(text)
        self.chat_view.add_assistant_start()
        self._set_status("Streaming response…")
        self._set_buddy_state("thinking", "Thinking")
        self._stream_task = asyncio.create_task(self._run_chat(text))

    def action_clear_chat(self) -> None:
        if self._stream_task is not None and not self._stream_task.done():
            self._stream_task.cancel()
        self.chat_view.clear()
        self.engine.history = SessionHistory()
        self._refresh_header()
        self._set_status("Cleared")
        self._set_buddy_state("idle")

    def action_cancel_streaming(self) -> None:
        if self._stream_task is None or self._stream_task.done():
            self._set_status("No active stream")
            return
        self._stream_task.cancel()
        self.chat_view.add_error("Streaming cancelled.")
        self.chat_view.add_assistant_end()
        self._set_status("Streaming cancelled")
        self._set_buddy_state("idle", "Cancelled")

    async def _run_chat(self, text: str) -> None:
        try:
            await self.engine.chat(
                text,
                on_text=self.chat_view.add_assistant_chunk,
                on_tool_start=self._handle_tool_start,
                on_tool_done=self._handle_tool_done,
            )
            self.chat_view.add_assistant_end()
            self._set_status("Ready")
            self._set_buddy_state("happy", "Done")
        except asyncio.CancelledError:
            self._set_status("Streaming cancelled")
            self._set_buddy_state("idle")
            return
        except Exception as exc:
            self.chat_view.add_error(str(exc))
            self.chat_view.add_assistant_end()
            self._set_status("Error")
            self._set_buddy_state("error", "Error")
        finally:
            self._refresh_header()
            self._stream_task = None

    def _handle_tool_start(self, name: str, tool_input: dict[str, Any]) -> None:
        summary = format_tool_args(name, tool_input)
        self.chat_view.add_tool_start(name, summary)
        self._set_status(f"Running {name}")
        self._set_buddy_state("thinking", name)

    def _handle_tool_done(self, name: str, result: ToolResult) -> None:
        output, exit_code = self._format_tool_result(name, result)
        self.chat_view.add_tool_result(output, exit_code)
        if result.is_error:
            self._set_status(f"{name} failed")
            self._set_buddy_state("error", name)
        else:
            self._set_status(f"{name} complete")
            self._set_buddy_state("happy", name)

    def _format_tool_result(self, name: str, result: ToolResult) -> tuple[str, int]:
        if name == "bash":
            payload = self._parse_bash_payload(result.as_text())
            if payload is not None:
                return (
                    format_bash_output(
                        str(payload.get("stdout", "")),
                        str(payload.get("stderr", "")),
                        int(payload.get("exit_code", 0)),
                    ),
                    int(payload.get("exit_code", 0)),
                )
        return result.as_text(), 1 if result.is_error else 0

    def _parse_bash_payload(self, text: str) -> dict[str, Any] | None:
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    async def _ask_permission(self, tool_name: str, tool_input: dict, category: ToolCategory) -> bool:
        if self.permission_mode in {PermissionMode.AUTO, PermissionMode.BYPASS}:
            return True
        if self.permission_mode == PermissionMode.PLAN:
            return category == ToolCategory.READ_ONLY
        result = await self.push_screen_wait(PermissionDialog(tool_name, tool_input))
        if result == "always":
            self.permission_mode = PermissionMode.AUTO
            self.permission_checker.mode = PermissionMode.AUTO
            return True
        return bool(result)

    def save_session(self) -> str:
        path = self.storage.save(self.engine.history)
        return str(path)

    def load_session(self, session_id: str) -> None:
        self.engine.history = self.storage.load(session_id)
        self.chat_view.clear()
        for message in self.engine.history.messages:
            text = "\n".join(str(block.get("text", block)) for block in message.content)
            if message.role == "user":
                self.chat_view.add_user_message(text)
            else:
                self.chat_view.add_assistant_start()
                if text:
                    self.chat_view.add_assistant_chunk(text)
                self.chat_view.add_assistant_end()
        self._refresh_header()
        self._set_status(f"Loaded {session_id}")

    def _refresh_header(self) -> None:
        tokens = self.engine.history.token_count()
        self.header_bar.update(f"PyClaudeCode ── {self.config.llm.model} ── {tokens} tokens")

    def _set_status(self, text: str) -> None:
        self.status_bar.update(text)
        self._refresh_header()

    def _set_buddy_state(self, state: str, bubble: str | None = None) -> None:
        if self.buddy is None:
            return
        self.buddy.set_state(state)
        if bubble:
            self.buddy.show_bubble(bubble)

    def _sync_buddy_visibility(self) -> None:
        if self.config.buddy.enabled:
            if self.buddy is None and BuddyWidget is not None:
                self.buddy = BuddyWidget()
                panel = Container(self.buddy, id="buddy-panel")
                self.query_one("#main-row", Container).mount(panel)
        elif self.buddy is not None:
            parent = self.buddy.parent
            self.buddy = None
            if parent is not None:
                parent.remove()


def run_app(config: Config) -> None:
    PyClaudeApp(config).run()
