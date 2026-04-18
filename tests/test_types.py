"""Tests for core types."""

import pytest
from cc.types.message import UserMessage, TextBlock, create_user_message
from cc.types.tool import ToolResult, tool_matches_name
from cc.types.permission import PermissionResult, PermissionDecision, PermissionRule


def test_user_message_creation():
    """Test creating a user message."""
    msg = create_user_message("Hello")
    assert msg.role == "user"
    assert len(msg.content) == 1
    assert msg.content[0].text == "Hello"


def test_text_block():
    """Test text block."""
    block = TextBlock(text="Test content")
    assert block.type == "text"
    assert block.text == "Test content"


def test_tool_result():
    """Test tool result."""
    result = ToolResult(content="Success")
    assert result.content == "Success"
    assert not result.is_error

    block = result.to_block("tool-123")
    assert block.tool_use_id == "tool-123"
    assert block.content == "Success"


def test_permission_result():
    """Test permission result."""
    result = PermissionResult(decision="allow")
    assert result.is_allowed
    assert not result.is_denied
    assert not result.needs_confirmation

    ask_result = PermissionResult(decision="ask")
    assert not ask_result.is_allowed
    assert ask_result.needs_confirmation


def test_permission_rule_match():
    """Test permission rule matching."""
    rule = PermissionRule(pattern="Bash(ls *)", decision=PermissionDecision.ALLOW)
    assert rule.matches("Bash", {"command": "ls -la"})
    assert not rule.matches("Bash", {"command": "rm file"})
    assert not rule.matches("Read", {})

    simple_rule = PermissionRule(pattern="Read", decision=PermissionDecision.ALLOW)
    assert simple_rule.matches("Read", {})
    assert not simple_rule.matches("Write", {})


def test_tool_matches_name():
    """Test tool name matching."""
    from cc.tools.bash import BashTool

    tool = BashTool()
    assert tool_matches_name(tool, "Bash")
    assert tool_matches_name(tool, "bash")  # lowercase match
    assert not tool_matches_name(tool, "Read")