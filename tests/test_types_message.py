"""Tests for message types."""

from __future__ import annotations
import pytest

from cc.types.message import (
    Message,
    UserMessage,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    create_user_message,
)


def test_create_user_message():
    """Test creating user message."""
    msg = create_user_message("Hello")
    assert msg.role == "user"
    assert len(msg.content) == 1
    assert isinstance(msg.content[0], TextBlock)
    assert msg.content[0].text == "Hello"


def test_user_message():
    """Test UserMessage creation."""
    msg = UserMessage(role="user", content=[TextBlock(text="Test")])
    assert msg.role == "user"
    assert len(msg.content) == 1


def test_assistant_message():
    """Test AssistantMessage creation."""
    msg = AssistantMessage(role="assistant", content=[TextBlock(text="Response")])
    assert msg.role == "assistant"
    assert len(msg.content) == 1


def test_tool_use_block():
    """Test ToolUseBlock creation."""
    block = ToolUseBlock(id="123", name="Bash", input={"command": "ls"})
    assert block.id == "123"
    assert block.name == "Bash"
    assert block.input == {"command": "ls"}


def test_tool_result_block():
    """Test ToolResultBlock creation."""
    block = ToolResultBlock(tool_use_id="123", content="output", is_error=False)
    assert block.tool_use_id == "123"
    assert block.content == "output"
    assert block.is_error == False


def test_message_with_multiple_blocks():
    """Test message with multiple content blocks."""
    msg = AssistantMessage(
        role="assistant",
        content=[
            TextBlock(text="Here's the result:"),
            ToolResultBlock(tool_use_id="123", content="output"),
        ],
    )
    assert len(msg.content) == 2


def test_text_block_type():
    """Test TextBlock type field."""
    block = TextBlock(text="Hello")
    assert block.type == "text"


def test_tool_use_block_type():
    """Test ToolUseBlock type field."""
    block = ToolUseBlock(id="123", name="Bash", input={})
    assert block.type == "tool_use"


def test_tool_result_block_type():
    """Test ToolResultBlock type field."""
    block = ToolResultBlock(tool_use_id="123", content="output")
    assert block.type == "tool_result"