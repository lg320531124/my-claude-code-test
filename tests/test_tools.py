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
    # description is a method, not a string attribute
    assert hasattr(tool, 'description')


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
    # content is a ReadOutput object
    if hasattr(result.content, 'file'):
        file_content = result.content.file.get('content', '')
        assert "Hello World" in file_content
    else:
        assert "Hello World" in str(result.content)


@pytest.mark.asyncio
async def test_write_tool(temp_dir, ctx):
    """Test WriteTool."""
    tool = WriteTool()
    # Use absolute path
    test_file = temp_dir / "new.txt"
    input = WriteInput(file_path=str(test_file), content="New content")
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert not result.is_error
    # Verify file was written
    assert test_file.exists()
    assert test_file.read_text() == "New content"


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
    # Should have error or file unchanged
    assert result.is_error or test_file.read_text() == "Hello World"


@pytest.mark.asyncio
async def test_glob_tool(temp_dir, ctx):
    """Test GlobTool."""
    # Create test files
    (temp_dir / "test.py").write_text("")
    (temp_dir / "test.txt").write_text("")
    (temp_dir / "other.py").write_text("")

    tool = GlobTool()
    input = GlobInput(pattern="*.py", path=str(temp_dir))
    ctx.cwd = str(temp_dir)

    result = await tool.execute(input, ctx)
    assert not result.is_error


@pytest.mark.asyncio
async def test_todo_tool():
    """Test TodoWriteTool."""
    clear_todos()

    from cc.tools.todo import TodoWriteTool, TodoWriteInput
    tool = TodoWriteTool()

    # Create input properly with TodoItem objects
    input = TodoWriteInput(
        todos=[
            TodoItem(content="Task 1", activeForm="Doing task 1"),
            TodoItem(content="Task 2"),
        ]
    )

    result = await tool.execute(input, None)
    assert not result.is_error