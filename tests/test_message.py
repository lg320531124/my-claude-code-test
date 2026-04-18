"""Tests for core types."""

import pytest
from cc.types.message import UserMessage, TextBlock


def test_user_message_creation():
    """Test creating a user message."""
    msg = UserMessage(content=[TextBlock(text="Hello")])
    assert msg.role == "user"
    assert len(msg.content) == 1
    assert msg.content[0].text == "Hello"


def test_text_block():
    """Test text block."""
    block = TextBlock(text="Test content")
    assert block.type == "text"
    assert block.text == "Test content"