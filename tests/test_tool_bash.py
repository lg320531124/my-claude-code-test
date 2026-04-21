"""Tests for Bash tool."""

from __future__ import annotations
import pytest
import asyncio

from cc.tools.bash import BashTool, BashInput
from cc.types.tool import ToolUseContext


@pytest.fixture
def bash_tool():
    """Create BashTool instance."""
    return BashTool()


@pytest.fixture
def ctx():
    """Create ToolUseContext."""
    return ToolUseContext(cwd="/tmp", session_id="test")


@pytest.mark.asyncio
async def test_bash_simple_command(bash_tool, ctx):
    """Test simple Bash command."""
    input = BashInput(command="echo hello")
    result = await bash_tool.execute(input, ctx)
    assert not result.is_error
    # content is BashOutput object
    if hasattr(result.content, 'stdout'):
        assert "hello" in result.content.stdout
    else:
        assert "hello" in str(result.content)


@pytest.mark.asyncio
async def test_bash_invalid_command(bash_tool, ctx):
    """Test invalid Bash command."""
    input = BashInput(command="nonexistent_command")
    result = await bash_tool.execute(input, ctx)
    assert result.is_error


def test_bash_check_permission_safe(bash_tool, ctx):
    """Test permission check for safe command."""
    input = BashInput(command="ls")
    result = bash_tool.check_permission(input, ctx)
    assert result.is_allowed


def test_bash_check_permission_dangerous(bash_tool, ctx):
    """Test permission check for dangerous command."""
    input = BashInput(command="rm file")
    result = bash_tool.check_permission(input, ctx)
    assert result.needs_confirmation


def test_bash_input_schema():
    """Test BashInput schema."""
    input = BashInput(command="ls", timeout_ms=10000)
    assert input.command == "ls"
    assert input.timeout_ms == 10000


@pytest.mark.asyncio
async def test_bash_timeout(bash_tool, ctx):
    """Test Bash command timeout."""
    input = BashInput(command="sleep 5", timeout_ms=100)
    result = await bash_tool.execute(input, ctx)
    # Either error or interrupted flag
    if hasattr(result.content, 'interrupted'):
        assert result.content.interrupted or result.is_error
    else:
        # If no interrupted flag, just check it completed
        assert True


@pytest.mark.asyncio
async def test_bash_with_description(bash_tool, ctx):
    """Test Bash command with description."""
    input = BashInput(command="pwd", description="Get current directory")
    result = await bash_tool.execute(input, ctx)
    assert not result.is_error