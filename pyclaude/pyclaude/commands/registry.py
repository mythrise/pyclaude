"""Slash command registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

Handler = Callable[[list[str], Any], str | Awaitable[str]]


@dataclass
class Command:
    name: str
    description: str
    usage: str
    handler: Handler


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def all(self) -> list[Command]:
        return list(self._commands.values())

    def completions(self, prefix: str) -> list[str]:
        return sorted(name for name in self._commands if name.startswith(prefix))

    async def execute(self, raw: str, app: Any) -> str:
        parts = raw.strip().split()
        name = parts[0][1:]
        command = self.get(name)
        if command is None:
            return f"Unknown command: /{name}"
        result = command.handler(parts[1:], app)
        if hasattr(result, "__await__"):
            return await result
        return str(result)
