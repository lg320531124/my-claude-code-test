"""Tests for Session."""

from __future__ import annotations
import pytest
import tempfile
from pathlib import Path

from cc.core.session import Session, SessionManager
from cc.types.message import UserMessage, AssistantMessage, TextBlock, create_user_message


@pytest.fixture
def session():
    """Create Session instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Session(cwd=tmpdir)


def test_session_creation(session):
    """Test Session creation."""
    assert session.cwd
    assert session.session_id
    assert session.messages == []


def test_session_add_message(session):
    """Test adding message to session."""
    msg = create_user_message("Hello")
    session.messages.append(msg)
    assert len(session.messages) == 1
    assert session.messages[0].role == "user"


def test_session_clear(session):
    """Test clearing session."""
    session.messages.append(create_user_message("test"))
    session.clear_messages()
    assert len(session.messages) == 0


def test_session_context(session):
    """Test Session context."""
    ctx = session.get_context()
    assert ctx.cwd == session.cwd
    assert ctx.session_id == session.session_id


def test_session_manager():
    """Test SessionManager."""
    manager = SessionManager()

    session1 = manager.create_session("/tmp")
    assert session1.session_id in manager.sessions

    session2 = manager.get_session(session1.session_id)
    assert session2 == session1

    manager.end_session(session1.session_id)
    assert session1.session_id not in manager.sessions


def test_session_metadata(session):
    """Test Session metadata."""
    session.metadata["test_key"] = "test_value"
    assert session.metadata["test_key"] == "test_value"


def test_session_git_status(session):
    """Test Session git status."""
    # In non-git directory
    assert session.git_branch is None or isinstance(session.git_branch, str)


def test_session_to_dict(session):
    """Test Session serialization."""
    session.messages.append(create_user_message("test"))
    data = session.to_dict()

    assert data["session_id"] == session.session_id
    assert data["cwd"] == session.cwd
    assert len(data["messages"]) == 1


def test_session_from_dict():
    """Test Session deserialization."""
    data = {
        "session_id": "test-123",
        "cwd": "/tmp",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "test"}]}],
        "metadata": {},
    }

    session = Session.from_dict(data)
    assert session.session_id == "test-123"
    assert session.cwd == "/tmp"
    assert len(session.messages) == 1