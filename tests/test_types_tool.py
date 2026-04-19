"""Tests for tool types."""

from __future__ import annotations
import pytest

from cc.types.tool import ToolDef, ToolResult, ToolUseContext
from cc.types.permission import PermissionResult, PermissionDecision


class MockTool(ToolDef):
    """Mock tool for testing."""

    name = "MockTool"
    description = "A mock tool for testing"
    input_schema = dict  # Simple schema

    async def execute(self, input: dict, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(content=f"Executed with: {input}")


def test_tool_result_creation():
    """Test ToolResult creation."""
    result = ToolResult(content="output")
    assert result.content == "output"
    assert result.is_error == False
    assert result.metadata == {}


def test_tool_result_error():
    """Test ToolResult with error."""
    result = ToolResult(content="error", is_error=True)
    assert result.is_error == True


def test_tool_result_metadata():
    """Test ToolResult with metadata."""
    result = ToolResult(content="output", metadata={"key": "value"})
    assert result.metadata == {"key": "value"}


def test_tool_result_to_block():
    """Test ToolResult to_block method."""
    result = ToolResult(content="output")
    block = result.to_block("tool_123")
    assert block.tool_use_id == "tool_123"
    assert block.content == "output"


def test_tool_use_context():
    """Test ToolUseContext creation."""
    ctx = ToolUseContext(cwd="/tmp", session_id="test")
    assert ctx.cwd == "/tmp"
    assert ctx.session_id == "test"


def test_tool_use_context_defaults():
    """Test ToolUseContext defaults."""
    ctx = ToolUseContext(cwd="/tmp", session_id="test")
    assert ctx.user_type == "external"
    assert ctx.permission_mode == "default"
    assert ctx.sandbox_enabled == False


def test_permission_result_allowed():
    """Test PermissionResult allowed."""
    result = PermissionResult(decision="allow")
    assert result.is_allowed == True
    assert result.is_denied == False
    assert result.needs_confirmation == False


def test_permission_result_denied():
    """Test PermissionResult denied."""
    result = PermissionResult(decision="deny", reason="test")
    assert result.is_allowed == False
    assert result.is_denied == True
    assert result.reason == "test"


def test_permission_result_ask():
    """Test PermissionResult ask."""
    result = PermissionResult(decision="ask")
    assert result.needs_confirmation == True


def test_mock_tool():
    """Test MockTool creation."""
    tool = MockTool()
    assert tool.name == "MockTool"
    assert tool.description == "A mock tool for testing"


@pytest.mark.asyncio
async def test_mock_tool_execute():
    """Test MockTool execution."""
    tool = MockTool()
    ctx = ToolUseContext(cwd="/tmp", session_id="test")
    result = await tool.execute({"test": "value"}, ctx)
    assert "test" in result.content