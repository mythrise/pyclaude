"""Base tool abstractions and default registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from pydantic import BaseModel, Field

from pyclaude.adapters.base import Tool


class ToolResult(BaseModel):
    content: list[dict] = Field(default_factory=list)
    is_error: bool = False

    def as_text(self) -> str:
        parts: list[str] = []
        for block in self.content:
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif block.get("type") == "image":
                source = block.get("source", {})
                media_type = source.get("media_type", "application/octet-stream")
                parts.append(f"[image:{media_type}]")
            else:
                parts.append(str(block))
        return "\n".join(part for part in parts if part)


class BaseTool(ABC):
    name: str
    description: str
    input_schema: dict

    @abstractmethod
    async def run(self, input: dict) -> ToolResult:
        raise NotImplementedError

    def to_anthropic_definition(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def to_anthropic_tools(self) -> list[Tool]:
        return [tool.to_anthropic_definition() for tool in self._tools.values()]

    @classmethod
    def default(cls) -> "ToolRegistry":
        from .bash import BashTool
        from .file_edit import FileEditTool
        from .file_read import FileReadTool
        from .file_write import FileWriteTool
        from .glob_tool import GlobTool
        from .grep_tool import GrepTool
        from .web_fetch import WebFetchTool

        registry = cls()
        for tool in (
            BashTool(),
            FileReadTool(),
            FileWriteTool(),
            FileEditTool(),
            GlobTool(),
            GrepTool(),
            WebFetchTool(),
        ):
            registry.register(tool)
        return registry

    def __iter__(self) -> Iterable[BaseTool]:
        return iter(self._tools.values())
