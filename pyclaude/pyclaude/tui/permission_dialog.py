"""Permission confirmation dialog."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class PermissionDialog(ModalScreen[bool | str]):
    def __init__(self, tool_name: str, tool_input: dict) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.tool_input = tool_input

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"Allow tool: {self.tool_name}")
            yield Static(str(self.tool_input))
            with Horizontal():
                yield Button("Yes", id="yes")
                yield Button("No", id="no")
                yield Button("Always", id="always")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "always":
            self.dismiss("always")
        else:
            self.dismiss(False)
