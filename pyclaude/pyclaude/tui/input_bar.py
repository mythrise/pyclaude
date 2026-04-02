"""Input bar widget."""

from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import TextArea


class InputBar(TextArea):
    class Submitted(Message):
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    BINDINGS = [
        ("ctrl+j", "submit", "Submit"),
        ("up", "history_prev", "History Prev"),
        ("down", "history_next", "History Next"),
    ]

    def __init__(self) -> None:
        super().__init__(id="input-bar")
        self.history: list[str] = []
        self.history_index = 0

    def on_mount(self) -> None:
        self.border_title = "Input"

    def action_submit(self) -> None:
        text = self.text.strip()
        if not text:
            return
        self.history.append(text)
        self.history_index = len(self.history)
        self.post_message(self.Submitted(text))
        self.clear()

    def action_history_prev(self) -> None:
        if not self.history:
            return
        self.history_index = max(0, self.history_index - 1)
        self.load_text(self.history[self.history_index])

    def action_history_next(self) -> None:
        if not self.history:
            return
        self.history_index = min(len(self.history), self.history_index + 1)
        self.load_text("" if self.history_index == len(self.history) else self.history[self.history_index])

    async def on_key(self, event: events.Key) -> None:
        if event.key == "/" and not self.text:
            self.load_text("/")
