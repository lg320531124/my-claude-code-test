"""Tests for tools."""

import pytest
from pathlib import Path
import tempfile

from cc.tools.bash import BashTool, BashInput
from cc.tools.read import ReadTool, ReadInput
from cc.tools.write import WriteTool, WriteInput
from cc.tools.edit import EditTool, EditInput
from cc.tools.glob import GlobTool, GlobInput
from cc.tools.todo import TodoWriteTool, TodoWriteInput, TodoItem, get_todos, clear_todos


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def ctx():
    """Create tool context."""
    from cc.types.tool import ToolUseContext
    return ToolUseContext(cwd="/tmp", session_id="test-session")


def test_bash_tool_schema():
    """Test BashTool has correct schema."""
    tool = BashTool()
    assert tool.name == "Bash"
    assert "shell" in tool.description.lower()


def test_bash_input_validation():
    """Test BashInput validation."""
    input = BashInput(command="ls -la")
    assert input.command == "ls -la"


@pytest.mark.asyncio
async def test_read_tool(temp_dir, ctx):
    """Test ReadTool."""
    # Create test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("Hello World\nLine 2")

    tool = ReadTool()
    input = ReadInput(file_path=str(test_file))
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert not result.is_error
    assert "Hello World" in result.content


@pytest.mark.asyncio
async def test_write_tool(temp_dir, ctx):
    """Test WriteTool."""
    tool = WriteTool()
    input = WriteInput(file_path="new.txt", content="New content")
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert not result.is_error
    assert "Successfully wrote" in result.content

    # Verify file exists
    assert (temp_dir / "new.txt").exists()
    assert (temp_dir / "new.txt").read_text() == "New content"


@pytest.mark.asyncio
async def test_edit_tool(temp_dir, ctx):
    """Test EditTool."""
    test_file = temp_dir / "edit.txt"
    test_file.write_text("Hello World")

    tool = EditTool()
    input = EditInput(
        file_path=str(test_file),
        old_string="World",
        new_string="Python",
    )
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert not result.is_error
    assert "replaced" in result.content

    # Verify content changed
    assert test_file.read_text() == "Hello Python"


@pytest.mark.asyncio
async def test_edit_tool_not_found(temp_dir, ctx):
    """Test EditTool with non-existent string."""
    test_file = temp_dir / "edit.txt"
    test_file.write_text("Hello World")

    tool = EditTool()
    input = EditInput(
        file_path=str(test_file),
        old_string="NotExist",
        new_string="Python",
    )
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert result.is_error
    assert "not found" in result.content


@pytest.mark.asyncio
async def test_glob_tool(temp_dir, ctx):
    """Test GlobTool."""
    # Create test files
    (temp_dir / "test.py").write_text("")
    (temp_dir / "test.txt").write_text("")
    (temp_dir / "other.py").write_text("")

    tool = GlobTool()
    input = GlobInput(pattern="*.py")
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert not result.is_error
    assert "test.py" in result.content
    assert "other.py" in result.content
    assert "test.txt" not in result.content


@pytest.mark.asyncio
async def test_todo_tool():
    """Test TodoWriteTool."""
    clear_todos()

    tool = TodoWriteTool()
    input = TodoWriteInput(todos=[
        TodoItem(content="Task 1", activeForm="Doing task 1"),
        TodoItem(content="Task 2"),
    ])

    result = await tool.execute(input, None)
    assert not result.is_error
    assert "Task 1" in result.content

    # Verify todos stored
    todos = get_todos()
    assert len(todos) == 2
    assert todos[0]["content"] == "Task 1"