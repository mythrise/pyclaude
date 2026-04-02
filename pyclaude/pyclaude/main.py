"""CLI entry point for pyclaude."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from pyclaude import __version__

app = typer.Typer(
    name="pyclaude",
    help="PyClaudeCode — Claude Code reimplemented in Python with local-model support.",
    add_completion=False,
    no_args_is_help=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pyclaude {__version__}")
        raise typer.Exit()


@app.command()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-V",
            help="Print version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
    backend: Annotated[
        str,
        typer.Option(
            "--backend",
            "-b",
            help="LLM backend to use: anthropic | ollama | openai_compat.",
            show_default=True,
        ),
    ] = "ollama",
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            "-m",
            help="Model name to pass to the backend (e.g. llama3.2, gpt-4o).",
        ),
    ] = None,
    no_buddy: Annotated[
        bool,
        typer.Option(
            "--no-buddy",
            help="Disable the companion sprite / buddy overlay.",
            is_flag=True,
        ),
    ] = False,
    auto: Annotated[
        bool,
        typer.Option(
            "--auto",
            help="Enable automatic permissions mode (no confirmation prompts).",
            is_flag=True,
        ),
    ] = False,
) -> None:
    """Start the PyClaudeCode TUI."""
    from pyclaude.config import get_config

    cfg = get_config()

    # CLI flags override persisted config
    cfg.llm.backend = backend
    if model is not None:
        cfg.llm.model = model
    if no_buddy:
        cfg.buddy.enabled = False
    if auto:
        cfg.permissions.mode = "auto"

    # Lazy import so TUI deps are only loaded when actually running
    from pyclaude.tui.app import run_app

    run_app(cfg)


if __name__ == "__main__":
    app()
