"""Buddy state machine."""

from __future__ import annotations

from enum import Enum


class BuddyState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    HAPPY = "happy"
    ERROR = "error"
    SLEEP = "sleep"


class BuddyStateMachine:
    def __init__(self) -> None:
        self.current = BuddyState.IDLE
        self._ticks = 0

    def on_thinking_start(self) -> BuddyState:
        self.current = BuddyState.THINKING
        self._ticks = 0
        return self.current

    def on_thinking_done(self, success: bool = True) -> BuddyState:
        self.current = BuddyState.HAPPY if success else BuddyState.ERROR
        self._ticks = 0
        return self.current

    def on_user_input(self) -> BuddyState:
        self.current = BuddyState.IDLE
        self._ticks = 0
        return self.current

    def tick(self) -> BuddyState:
        self._ticks += 1
        if self.current in {BuddyState.HAPPY, BuddyState.ERROR} and self._ticks >= 2:
            self.current = BuddyState.IDLE
        elif self.current == BuddyState.IDLE and self._ticks >= 10:
            self.current = BuddyState.SLEEP
        return self.current
