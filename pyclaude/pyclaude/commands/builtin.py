"""Built-in slash commands."""

from __future__ import annotations

from pyclaude import __version__
from pyclaude.session.compressor import compress_history

from .registry import Command, CommandRegistry


def register_builtins(registry: CommandRegistry, app) -> None:
    registry.register(Command("help", "List commands", "/help", lambda _a, _app: _help_text(registry)))
    registry.register(Command("clear", "Clear chat", "/clear", lambda _a, app: _clear(app)))
    registry.register(Command("exit", "Exit app", "/exit", lambda _a, app: _exit(app)))
    registry.register(Command("version", "Show version", "/version", lambda _a, _app: __version__))
    registry.register(Command("config", "Show config", "/config", lambda _a, app: str(app.config)))
    registry.register(Command("cost", "Show token usage", "/cost", lambda _a, app: str(app.engine.history.total_tokens)))
    registry.register(Command("compact", "Compact session", "/compact", lambda _a, app: _compact(app)))
    registry.register(Command("resume", "Resume session", "/resume <id>", lambda a, app: _resume(a, app)))
    registry.register(Command("buddy", "Toggle buddy", "/buddy", lambda _a, app: _toggle_buddy(app)))
    registry.register(Command("dream", "Toggle autoDream", "/dream", lambda _a, app: _toggle_dream(app)))


def _help_text(registry: CommandRegistry) -> str:
    return "\n".join(f"/{cmd.name} - {cmd.description}" for cmd in registry.all())


def _clear(app) -> str:
    app.action_clear_chat()
    return "Chat cleared."


def _exit(app) -> str:
    app.exit()
    return "Exiting."


async def _compact(app) -> str:
    app.engine.history = await compress_history(app.engine.history, app.engine.adapter)
    return "Session compacted."


def _resume(args: list[str], app) -> str:
    if not args:
        sessions = app.storage.list_sessions()
        return "\n".join(f"{item.session_id} {item.first_message}" for item in sessions)
    app.load_session(args[0])
    return f"Resumed {args[0]}"


def _toggle_buddy(app) -> str:
    app.config.buddy.enabled = not app.config.buddy.enabled
    return f"Buddy {'enabled' if app.config.buddy.enabled else 'disabled'}."


def _toggle_dream(app) -> str:
    app.config.autodream.enabled = not app.config.autodream.enabled
    return f"autoDream {'enabled' if app.config.autodream.enabled else 'disabled'}."
