"""Tests for BashTool."""

import pytest
from cc.tools.bash import BashTool, BashInput


def test_bash_tool_schema():
    """Test BashTool has correct schema."""
    tool = BashTool()
    assert tool.name == "Bash"
    assert "shell" in tool.description_text.lower()


def test_bash_input_validation():
    """Test BashInput validation."""
    input = BashInput(command="ls -la")
    assert input.command == "ls -la"