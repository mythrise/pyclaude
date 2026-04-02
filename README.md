#```
#  ____        ____ _                 _      ____          _
# |  _ \ _   _/ ___| | __ _ _   _  __| | ___/ ___|___   __| | ___
# | |_) | | | | |   | |/ _` | | | |/ _` |/ _ \ |   / _ \ / _` |/ _ \
# |  __/| |_| | |___| | (_| | |_| | (_| |  __/ |__| (_) | (_| |  __/
# |_|    \__, |\____|_|\__,_|\__,_|\__,_|\___|\____\___/ \__,_|\___|
#        |___/
#```

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-5c6ac4)

**PyClaudeCode** is a customizable AI coding assistant harness: an open-source Python reimplementation of Claude Code, built for local models, real tool use, and terminal-native flow.

## Why PyClaudeCode

- **Runs where you want it to run.** Use Anthropic, Ollama, or any OpenAI-compatible endpoint such as LM Studio or LocalAI.
- **Feels like a real coding assistant, not a chatbot wrapper.** Multi-turn conversation, streaming output, tool execution, slash commands, session resume, and context compaction are all part of the core loop.
- **Built as a harness, not a dead end.** Adapters, tools, commands, permissions, and the Textual UI are all designed to be swapped and extended.
- **Includes two historically interesting extras.** The Buddy companion sprite and autoDream background tasks are sourced from Claude Code's internal `buddy/` and `autoDream/` directories and were never publicly released before this project.

## Features

### Core conversation engine

- Full multi-turn conversation engine
- Streaming assistant output in the TUI
- Session persistence and resume from `~/.pyclaude/sessions/`
- Context compression with `/compact`

### Tool use

- Tool-calling loop with parallel execution via `asyncio.gather`
- 7 core tools included out of the box:
  - `Bash`
  - `FileRead`
  - `FileWrite`
  - `FileEdit`
  - `Glob`
  - `Grep`
  - `WebFetch`

### Model backends

- `anthropic` for the Anthropic API
- `ollama` for local models
- `openai_compat` for OpenAI-style APIs including LM Studio and LocalAI

### Safety and permissions

- 4 permission modes:
  - `default` for prompt-before-action
  - `plan` for read-only execution
  - `auto` for fully automatic approvals
  - `bypass` for unrestricted execution
- Dangerous bash command detection for known destructive patterns such as `rm -rf /` and fork bombs

### Textual TUI

- Markdown rendering
- Syntax highlighting
- Streaming display
- Red/green diff highlighting
- Command palette style slash-command workflow

### Built-in commands

- `/help`
- `/clear`
- `/cost`
- `/compact`
- `/resume`
- `/config`
- `/buddy`
- `/dream`

## Unreleased Features

These two features deserve their own spotlight.

### Buddy companion sprite

PyClaudeCode includes an ASCII cat companion sourced from Claude Code's internal `buddy/` directory. It was never publicly released before.

- 5 emotion states
- Animation support
- Bubble notifications
- Optional side-panel companion inside the Textual UI

Buddy showcase:

```text
Idle        Thinking     Happy        Error        Sleepy

 /\_/\      /\_/\        /\_/\        /\_/\        /\_/\ zZ
( o.o )    ( -.- )      ( ^.^ )      ( x.x )      ( -.- )
 > ^ <      > ^ <        > ^ <        > ^ <        > ^ <
```

### autoDream auto-tasks

PyClaudeCode also includes `autoDream`, sourced from Claude Code's internal `autoDream/` directory and likewise never publicly released before.

It can run background tasks after an idle period, including:

- TODO / FIXME scanning
- brief code review observations
- documentation gap checks

This is not positioned as a full autonomous agent swarm. It is a lightweight idle-time task runner built into the harness.

## Terminal Mockup

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ PyClaudeCode ── llama3.2 ── 4821 tokens                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ User                                                                        │
│ Refactor the session loader and show me the diff.                           │
│                                                                              │
│ Assistant                                                                    │
│ I'll inspect the storage layer, update the loader, and summarize the change.│
│                                                                              │
│ Tool: Grep                                                                   │
│ pyclaude/session/storage.py:18:def load(self, session_id: str) -> ...       │
│                                                                              │
│ Tool: FileEdit                                                               │
│ - old_path = path / session_id                                               │
│ + old_path = self.base_dir / f"{session_id}.json"                            │
│                                                                              │
│ Assistant                                                                    │
│ Done. The loader now resolves session files consistently and resume works.   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Status: Ready                                             Buddy: (^.^) Done │
├──────────────────────────────────────────────────────────────────────────────┤
│ Input                                                                        │
│ /compact                                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
Ctrl+J submit   Ctrl+L clear   Esc cancel stream   Ctrl+C quit
```

## 🧠 The Harness Architecture

PyClaudeCode is intentionally layered. You can replace the model backend, add tools, customize permissions, register commands at runtime, or restyle the TUI without rewriting the whole app.

### Adapter layer

Implement `BaseLLMAdapter` to connect any backend: Gemini, Mistral, self-hosted inference, or something stranger.

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMAdapter(ABC):
    @abstractmethod
    async def stream(
        self,
        messages: list,
        tools: list,
        system: str,
        max_tokens: int,
    ) -> AsyncIterator:
        ...

    @abstractmethod
    def format_tool_result(
        self,
        tool_use_id: str,
        content: str,
        is_error: bool = False,
    ) -> dict:
        ...
```

The project ships with:

- `AnthropicAdapter`
- `OllamaAdapter`
- `OpenAICompatAdapter`

### Tool layer

Extend `BaseTool`, then register your tool with `ToolRegistry`.

```python
from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str
    description: str
    input_schema: dict

    @abstractmethod
    async def run(self, input: dict):
        ...
```

The default registry wires in:

- `BashTool`
- `FileReadTool`
- `FileWriteTool`
- `FileEditTool`
- `GlobTool`
- `GrepTool`
- `WebFetchTool`

### Permission layer

Permissions are a first-class part of the harness. The built-in `PermissionChecker` supports the four shipped modes and blocks known destructive commands. If your environment needs stricter policy, this is one of the cleanest extension points.

### Command layer

`CommandRegistry` handles dynamic slash-command registration, which keeps command behavior separate from the TUI shell itself.

### TUI layer

The interface is built on Textual. Widgets, layout, and CSS theme behavior can all be customized without touching the conversation engine.

## 🚀 Quick Start

### 1. Install

```bash
cd pyclaude
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure a backend

PyClaudeCode reads configuration from `~/.pyclaude/config.toml`.

```toml
[llm]
backend = "ollama"
model = "llama3.2"
base_url = "http://localhost:11434"
api_key = ""
max_tokens = 8192
temperature = 0.0

[permissions]
mode = "default"

[buddy]
enabled = true

[autodream]
enabled = false
idle_threshold = 300
tasks = ["todo_scanner"]
```

### 3. Run it

```bash
pyclaude
```

Useful startup flags:

```bash
pyclaude --backend ollama --model llama3.2
pyclaude --backend anthropic --model claude-3-7-sonnet-latest
pyclaude --auto
pyclaude --no-buddy
```

## 🔌 Backend Configuration

All backends are configured through `~/.pyclaude/config.toml`.

### Anthropic API

```toml
[llm]
backend = "anthropic"
model = "claude-3-7-sonnet-latest"
base_url = "https://api.anthropic.com"
api_key = "your-anthropic-api-key"
max_tokens = 8192
temperature = 0.0
```

### Ollama

```toml
[llm]
backend = "ollama"
model = "llama3.2"
base_url = "http://localhost:11434"
api_key = ""
max_tokens = 8192
temperature = 0.0
```

### OpenAI-compatible endpoints

Works with servers that expose an OpenAI-style API, including LM Studio and LocalAI.

```toml
[llm]
backend = "openai_compat"
model = "local-model"
base_url = "http://localhost:1234/v1"
api_key = "not-needed-or-your-local-key"
max_tokens = 8192
temperature = 0.0
```

## ⌨️ TUI Keybindings

| Key | Action |
| --- | --- |
| `Ctrl+J` | Submit the current prompt |
| `Ctrl+L` | Clear the current chat |
| `Esc` | Cancel active streaming |
| `Ctrl+C` | Quit the app |
| `Up` | Previous input history entry |
| `Down` | Next input history entry |

## 💬 Commands

| Command | Description |
| --- | --- |
| `/help` | List available slash commands |
| `/clear` | Clear the current chat session |
| `/cost` | Show token usage |
| `/compact` | Compress the current session context |
| `/resume` | List resumable sessions or resume by ID |
| `/config` | Print the current config |
| `/buddy` | Toggle the Buddy companion |
| `/dream` | Toggle autoDream |

## 🧩 Extending PyClaudeCode

### Add a custom tool

```python
from pyclaude.tools.base import BaseTool, ToolResult


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Show the current git status."
    input_schema = {
        "type": "object",
        "properties": {},
    }

    async def run(self, input: dict) -> ToolResult:
        return ToolResult(content=[{"type": "text", "text": "git status output"}])
```

Then register it:

```python
from pyclaude.tools.base import ToolRegistry

registry = ToolRegistry.default()
registry.register(GitStatusTool())
```

### Add a custom backend adapter

```python
from pyclaude.adapters.base import BaseLLMAdapter


class MyAdapter(BaseLLMAdapter):
    async def stream(self, messages, tools, system, max_tokens):
        ...

    def format_tool_result(self, tool_use_id, content, is_error=False):
        ...
```

Once you have an adapter implementation, wire it into the adapter factory or your own app bootstrap path.

### Customize permissions, commands, and UI

- Swap or wrap the permission checker for custom approval logic
- Register commands dynamically through `CommandRegistry`
- Restyle the Textual interface with custom widgets and CSS themes

## 🛣️ Roadmap

- MCP support
- Multi-agent workflows
- Vim-style editing mode
- More built-in tools
- More TUI themes
- Richer autoDream task packs
- Additional model adapters

## 🤝 Contributing

Issues, fixes, experiments, and backend/tool extensions are all welcome.

If you contribute, optimize for the project's actual shape:

- keep the harness modular
- avoid backend-specific assumptions leaking into the core engine
- preserve the safety model around permissions and destructive commands
- document new commands, tools, and adapters clearly

## 📄 License

MIT
