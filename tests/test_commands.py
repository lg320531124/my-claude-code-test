"""Tests for commands."""

import pytest
from pathlib import Path
import tempfile
import asyncio

from cc.commands.doctor import check_python_async, check_git_async, check_ripgrep_async


@pytest.mark.asyncio
async def test_check_python():
    """Test Python check."""
    result = await check_python_async()
    assert result.ok
    assert "Python" in result.name


@pytest.mark.asyncio
async def test_check_git():
    """Test git check."""
    result = await check_git_async()
    assert result.name == "Git"


@pytest.mark.asyncio
async def test_check_ripgrep():
    """Test ripgrep check."""
    result = await check_ripgrep_async()
    assert result.name == "Ripgrep"


@pytest.mark.asyncio
async def test_estimate_context_usage():
    """Test context estimation."""
    from cc.commands.compact import estimate_context_usage
    from cc.types.message import UserMessage, TextBlock

    messages = [
        UserMessage(content=[TextBlock(text="Hello world this is a test message")]),
        UserMessage(content=[TextBlock(text="Another message with some more text")]),
    ]

    usage = estimate_context_usage(messages)
    assert usage["message_count"] == 2
    assert usage["estimated_tokens"] > 0


@pytest.mark.asyncio
async def test_compact_messages():
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