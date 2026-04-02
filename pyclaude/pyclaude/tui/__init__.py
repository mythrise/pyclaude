"""TUI exports."""

try:
    from .app import PyClaudeApp, run_app
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    PyClaudeApp = None

    def run_app(*_args, **_kwargs):
        raise RuntimeError("textual is not installed")


__all__ = ["PyClaudeApp", "run_app"]
