"""Permission mode enums."""

from __future__ import annotations

from enum import Enum


class PermissionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"
    AUTO = "auto"
    BYPASS = "bypass"


class ToolCategory(str, Enum):
    READ_ONLY = "read_only"
    FILE_WRITE = "file_write"
    BASH = "bash"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"
