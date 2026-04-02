"""Animated ASCII buddy widget."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

SPRITES: dict[str, list[str]] = {
    "idle": [
        r""" /\_/\\
( o.o )
 > ^ <""",
        r""" /\_/\\
( -.- )
 > ^ <""",
        r""" /\_/\\
( o.o )
 >>^<<""",
    ],
    "thinking": [
        r""" /\_/\\
( o.O )
 > ^ <""",
        r""" /\_/\\
( O.o )
 > ^ <""",
        r""" /\_/\\
( -.- )
 > ^ <""",
    ],
    "happy": [
        r""" /\_/\\
( ^.^ )
 > ^ <""",
        r""" /\_/\\
( ^o^ )
 > ^ <""",
        r""" /\_/\\
( ^.^ )
 >>^<<""",
    ],
    "error": [
        r""" /\_/\\
( x.x )
 > ^ <""",
        r""" /\_/\\
( X.X )
 > ^ <""",
        r""" /\_/\\
( ;_; )
 > ^ <""",
    ],
    "sleep": [
        r""" /\_/\\
( -.- ) z
 > ^ <""",
        r""" /\_/\\
( -.- ) zz
 > ^ <""",
        r""" /\_/\\
( -.- ) zzz
 > ^ <""",
    ],
}


class BuddyWidget(Widget):
    DEFAULT_CSS = """
    BuddyWidget {
        width: 16;
        height: 8;
        content-align: center middle;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="buddy")
        self._state = "idle"
        self._frame = 0
        self._bubble_text = ""
        self._bubble_timer = 0

    def on_mount(self) -> None:
        self.set_interval(0.5, self._tick)

    def _tick(self) -> None:
        frames = SPRITES.get(self._state, SPRITES["idle"])
        self._frame = (self._frame + 1) % len(frames)
        if self._bubble_timer > 0:
            self._bubble_timer -= 1
            if self._bubble_timer == 0:
                self._bubble_text = ""
        self.refresh()

    def show_bubble(self, text: str, duration: int = 6) -> None:
        self._bubble_text = text.strip()
        self._bubble_timer = max(1, duration * 2) if self._bubble_text else 0
        self.refresh()

    def set_state(self, state: str) -> None:
        self._state = state if state in SPRITES else "idle"
        self._frame = 0
        self.refresh()

    def render(self) -> Text:
        content = Text(justify="center")
        if self._bubble_text:
            content.append(f"╭ {self._bubble_text[:12]} ╮\n", style="bold #58a6ff")
        sprite = SPRITES.get(self._state, SPRITES["idle"])[self._frame]
        content.append(sprite, style="bold #e6edf3")
        return content
