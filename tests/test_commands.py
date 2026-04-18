"""Tests for commands."""

import pytest
from pathlib import Path
import tempfile

from cc.commands.doctor import check_python, check_git, check_ripgrep
from cc.commands.commit import get_git_info
from cc.commands.compact import estimate_context_usage


def test_check_python():
    """Test Python check."""
    result = check_python()
    assert result["ok"]
    assert "Python" in result["name"]


def test_check_git():
    """Test git check."""
    result = check_git()
    # Git might or might not be installed
    assert result["name"] == "Git"


def test_check_ripgrep():
    """Test ripgrep check."""
    result = check_ripgrep()
    assert result["name"] == "Ripgrep"


def test_estimate_context_usage():
    """Test context estimation."""
    from cc.types.message import UserMessage, TextBlock

    messages = [
        UserMessage(content=[TextBlock(text="Hello world this is a test message")]),
        UserMessage(content=[TextBlock(text="Another message with some more text")]),
    ]

    usage = estimate_context_usage(messages)
    assert usage["message_count"] == 2
    assert usage["estimated_tokens"] > 0


def test_compact_messages():
    """Test message compacting."""
    from cc.commands.compact import run_compact
    from cc.core.session import Session
    from rich.console import Console
    from cc.types.message import UserMessage, TextBlock

    console = Console()

    with tempfile.TemporaryDirectory() as d:
        session = Session(cwd=Path(d))

        # Add many messages
        for i in range(10):
            msg = UserMessage(content=[TextBlock(text=f"Message {i}" * 50)])
            session.add_message(msg)

        assert len(session.messages) == 10

        # Compact
        run_compact(console, session)

        # Should have fewer messages
        assert len(session.messages) < 10