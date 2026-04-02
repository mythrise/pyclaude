import asyncio
from pathlib import Path

from pyclaude.tools import BashTool, FileEditTool, FileReadTool, FileWriteTool


def test_bash_tool_runs_command() -> None:
    result = asyncio.run(BashTool().run({"command": "printf 'hello'"}))
    assert not result.is_error
    assert "hello" in result.as_text()


def test_bash_tool_blocks_dangerous_command() -> None:
    result = asyncio.run(BashTool().run({"command": "rm -rf /"}))
    assert result.is_error


def test_file_read_with_line_numbers(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    result = asyncio.run(FileReadTool().run({"path": str(path), "offset": 1, "limit": 1}))
    assert "2" in result.as_text()
    assert "two" in result.as_text()


def test_file_write_and_edit(tmp_path: Path) -> None:
    path = tmp_path / "b.txt"
    asyncio.run(FileWriteTool().run({"path": str(path), "content": "hello world"}))
    result = asyncio.run(FileEditTool().run(
        {"path": str(path), "old_string": "world", "new_string": "python"}
    ))
    assert not result.is_error
    assert "python" in path.read_text(encoding="utf-8")
