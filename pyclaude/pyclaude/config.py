"""Configuration system for pyclaude.

Config is stored as TOML at ~/.pyclaude/config.toml.
Call ``get_config()`` for a process-level singleton; ``load_config()`` to
force a fresh read from disk; ``save_config(cfg)`` to persist changes.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomli_w
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    tomli_w = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CONFIG_DIR: Path = Path.home() / ".pyclaude"
CONFIG_FILE: Path = CONFIG_DIR / "config.toml"
SESSIONS_DIR: Path = CONFIG_DIR / "sessions"

# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    """Settings for the language-model backend."""

    backend: str = "ollama"  # "anthropic" | "ollama" | "openai_compat"
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    max_tokens: int = 8192
    temperature: float = 0.0


@dataclass
class BuddyConfig:
    """Settings for the companion sprite overlay."""

    enabled: bool = True
    sprite_type: str = "default"
    position: str = "bottom-right"


@dataclass
class AutoDreamConfig:
    """Settings for the auto-dream idle-task runner."""

    enabled: bool = False
    idle_threshold: int = 300  # seconds before triggering a dream cycle
    tasks: list[str] = field(default_factory=lambda: ["todo_scanner"])


@dataclass
class PermissionsConfig:
    """Settings for the permission / confirmation system."""

    mode: str = "default"  # "default" | "plan" | "auto" | "bypass"


@dataclass
class Config:
    """Root configuration object."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    buddy: BuddyConfig = field(default_factory=BuddyConfig)
    autodream: AutoDreamConfig = field(default_factory=AutoDreamConfig)
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)


# ---------------------------------------------------------------------------
# (De)serialisation helpers
# ---------------------------------------------------------------------------


def _dict_to_llm(d: dict[str, Any]) -> LLMConfig:
    return LLMConfig(
        backend=str(d.get("backend", LLMConfig.backend)),
        model=str(d.get("model", LLMConfig.model)),
        base_url=str(d.get("base_url", LLMConfig.base_url)),
        api_key=str(d.get("api_key", LLMConfig.api_key)),
        max_tokens=int(d.get("max_tokens", LLMConfig.max_tokens)),
        temperature=float(d.get("temperature", LLMConfig.temperature)),
    )


def _dict_to_buddy(d: dict[str, Any]) -> BuddyConfig:
    return BuddyConfig(
        enabled=bool(d.get("enabled", BuddyConfig.enabled)),
        sprite_type=str(d.get("sprite_type", BuddyConfig.sprite_type)),
        position=str(d.get("position", BuddyConfig.position)),
    )


def _dict_to_autodream(d: dict[str, Any]) -> AutoDreamConfig:
    raw_tasks = d.get("tasks")
    tasks: list[str] = list(raw_tasks) if isinstance(raw_tasks, list) else ["todo_scanner"]
    return AutoDreamConfig(
        enabled=bool(d.get("enabled", AutoDreamConfig.enabled)),
        idle_threshold=int(d.get("idle_threshold", AutoDreamConfig.idle_threshold)),
        tasks=tasks,
    )


def _dict_to_permissions(d: dict[str, Any]) -> PermissionsConfig:
    return PermissionsConfig(
        mode=str(d.get("mode", PermissionsConfig.mode)),
    )


def _config_from_dict(data: dict[str, Any]) -> Config:
    return Config(
        llm=_dict_to_llm(data.get("llm", {})),
        buddy=_dict_to_buddy(data.get("buddy", {})),
        autodream=_dict_to_autodream(data.get("autodream", {})),
        permissions=_dict_to_permissions(data.get("permissions", {})),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config() -> Config:
    """Read config from disk, creating default files/dirs if absent."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        default = Config()
        save_config(default)
        return default

    with CONFIG_FILE.open("rb") as fh:
        data: dict[str, Any] = tomllib.load(fh)

    return _config_from_dict(data)


def save_config(config: Config) -> None:
    """Serialise *config* to TOML and write to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # dataclasses.asdict gives us a plain dict tree suitable for tomli_w
    data: dict[str, Any] = asdict(config)

    if tomli_w is not None:
        with CONFIG_FILE.open("wb") as fh:
            tomli_w.dump(data, fh)
        return
    CONFIG_FILE.write_text(_dict_to_toml(data), encoding="utf-8")


def _dict_to_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        if isinstance(values, dict):
            for key, value in values.items():
                lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# Singleton cache
# ---------------------------------------------------------------------------

_config_cache: Config | None = None


def get_config() -> Config:
    """Return the process-level Config singleton.

    The config is loaded from disk on first call and cached for the lifetime
    of the process.  To force a reload (e.g. after the user edits the file),
    call ``load_config()`` directly and replace the cache::

        import pyclaude.config as _cfg
        _cfg._config_cache = _cfg.load_config()
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache
