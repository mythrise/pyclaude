"""Project-wide constants for pyclaude."""

from __future__ import annotations

APP_NAME: str = "pyclaude"
VERSION: str = "0.1.0"

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------
# Available placeholders (filled at runtime by the agent core):
#   {cwd}       — current working directory
#   {platform}  — sys.platform string  (e.g. "darwin", "linux", "win32")
#   {datetime}  — ISO-8601 local datetime string

DEFAULT_SYSTEM_PROMPT: str = """\
You are PyClaudeCode, an AI software-engineering assistant running locally on \
the user's machine.

Environment:
  Working directory : {cwd}
  Platform          : {platform}
  Date / time       : {datetime}

You have access to a set of tools that let you read and write files, run shell \
commands, search codebases, browse the web, and more.  Use them proactively to \
complete the user's requests accurately and efficiently.

Guidelines:
- Always prefer editing existing files over creating new ones unless a new file \
is genuinely required.
- When running shell commands, prefer non-destructive operations and confirm \
with the user before anything irreversible.
- Keep responses concise.  Show code snippets only when the exact text is \
load-bearing.
- If you are uncertain about a requirement, ask a clarifying question rather \
than guessing.
- Respect the active permissions mode.  In "plan" mode, propose steps and wait \
for approval.  In "auto" mode you may proceed without confirmation.
"""

# ---------------------------------------------------------------------------
# Operational limits
# ---------------------------------------------------------------------------

# Maximum bytes of tool output kept before truncating tail content
MAX_OUTPUT_TRUNCATION: int = 100_000  # bytes

# Seconds before a tool invocation is forcibly cancelled
TOOL_TIMEOUT: int = 120  # seconds

# Approximate token count that triggers a conversation compaction / summary
COMPACT_THRESHOLD: int = 50_000  # tokens
