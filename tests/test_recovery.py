"""Tests for session recovery."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import json
import time

from cc.core.recovery import (
    SessionPersistence,
    SessionRecovery,
    SessionHistory,
    SessionMetadata,
    SessionData,
)
from cc.core.session import Session


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def test_session():
    """Create test session."""
    return Session(cwd=Path("/tmp/test"), session_id="test-123")


def test_session_metadata():
    """Test session metadata."""
    metadata = SessionMetadata(
        session_id="test-123",
        cwd="/tmp/test",
        created_at=time.time(),
        updated_at=time.time(),
        message_count=5,
        token_count=1000,
        model="claude-sonnet-4-6",
        title="Test session",
    )

    assert metadata.session_id == "test-123"
    assert metadata.message_count == 5


def test_session_persistence_init(temp_storage):
    """Test persistence initialization."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    assert persistence.storage_dir == temp_storage
    assert persistence.max_sessions == 50


def test_session_persistence_save(temp_storage, test_session):
    """Test saving session."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    stats = {"total_tokens": 500}
    config = {"model": "test-model"}

    path = persistence.save(test_session, stats, config)

    assert path.exists()
    assert path.suffix == ".json"

    # Load and verify
    data = json.loads(path.read_text())
    assert data["metadata"]["session_id"] == "test-123"
    assert data["stats"]["total_tokens"] == 500


def test_session_persistence_load(temp_storage, test_session):
    """Test loading session."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    # Save first
    path = persistence.save(test_session, {}, {})

    # Then load
    data = persistence.load(path)

    assert data is not None
    assert data.metadata.session_id == "test-123"


def test_session_persistence_list(temp_storage, test_session):
    """Test listing sessions."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    # Save multiple sessions
    for i in range(3):
        session = Session(session_id=f"session-{i}")
        persistence.save(session, {}, {})

    sessions = persistence.list_sessions()
    assert len(sessions) == 3


def test_session_persistence_load_by_id(temp_storage):
    """Test loading session by ID."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    session = Session(session_id="unique-123")
    persistence.save(session, {}, {})

    data = persistence.load_by_id("unique-123")
    assert data is not None
    assert data.metadata.session_id == "unique-123"


def test_session_persistence_delete(temp_storage, test_session):
    """Test deleting session."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    path = persistence.save(test_session, {}, {})

    assert path.exists()

    persistence.delete(path)

    assert not path.exists()


def test_session_persistence_cleanup(temp_storage):
    """Test cleanup of old sessions."""
    persistence = SessionPersistence(storage_dir=temp_storage, max_sessions=2)

    # Create more than max_sessions
    for i in range(5):
        session = Session(session_id=f"session-{i}")
        persistence.save(session, {}, {})

    sessions = persistence.list_sessions()
    assert len(sessions) <= 2


def test_session_recovery_init(temp_storage):
    """Test recovery initialization."""
    persistence = SessionPersistence(storage_dir=temp_storage)
    recovery = SessionRecovery(persistence)

    assert recovery.persistence == persistence
    assert not recovery.recovery_file.exists()


def test_session_recovery_check(temp_storage, test_session):
    """Test checking for recovery."""
    persistence = SessionPersistence(storage_dir=temp_storage)
    recovery = SessionRecovery(persistence)

    # No recovery initially
    result = recovery.check_recovery()
    assert result is None

    # Save and write recovery marker
    path = persistence.save(test_session, {}, {})
    recovery._write_recovery_file(path)

    # Check again
    result = recovery.check_recovery()
    assert result is not None


def test_session_recovery_clear(temp_storage, test_session):
    """Test clearing recovery."""
    persistence = SessionPersistence(storage_dir=temp_storage)
    recovery = SessionRecovery(persistence)

    path = persistence.save(test_session, {}, {})
    recovery._write_recovery_file(path)

    assert recovery.recovery_file.exists()

    recovery.clear_recovery()

    assert not recovery.recovery_file.exists()


def test_session_history(temp_storage):
    """Test session history."""
    persistence = SessionPersistence(storage_dir=temp_storage)
    history = SessionHistory(persistence)

    # Add some sessions
    for i in range(5):
        session = Session(session_id=f"history-{i}")
        persistence.save(session, {}, {})

    recent = history.get_recent(limit=3)
    assert len(recent) == 3


def test_session_history_search(temp_storage):
    """Test searching sessions."""
    persistence = SessionPersistence(storage_dir=temp_storage)
    history = SessionHistory(persistence)

    # Create session with specific cwd
    session = Session(session_id="search-1", cwd=Path("/project/myapp"))
    persistence.save(session, {}, {})

    results = history.search("myapp")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_session_auto_save(temp_storage, test_session):
    """Test auto-save functionality."""
    persistence = SessionPersistence(storage_dir=temp_storage)
    recovery = SessionRecovery(persistence)

    # Mock engine and config
    engine = type("Engine", (), {
        "get_context_summary": lambda: {"total_tokens": 100},
    })()
    config = type("Config", (), {
        "api": type("API", (), {"model": "test-model"})(),
    })()

    # Start auto-save with short interval
    recovery._auto_save_interval = 0.1
    recovery.start_auto_save(test_session, engine, config)

    # Wait a bit
    await asyncio.sleep(0.3)

    # Stop
    recovery.stop_auto_save()

    # Check if sessions were saved
    sessions = persistence.list_sessions()
    assert len(sessions) >= 1


def test_session_data():
    """Test session data structure."""
    metadata = SessionMetadata(
        session_id="data-123",
        cwd="/tmp",
        created_at=time.time(),
        updated_at=time.time(),
        message_count=0,
        token_count=0,
        model="",
    )

    data = SessionData(
        metadata=metadata,
        messages=[],
        stats={},
        config={},
    )

    assert data.metadata.session_id == "data-123"
    assert data.messages == []


def test_restore_session(temp_storage):
    """Test restoring session from data."""
    persistence = SessionPersistence(storage_dir=temp_storage)

    # Create and save session
    original = Session(session_id="restore-123", cwd=Path("/restore/path"))
    path = persistence.save(original, {}, {})

    # Load data
    data = persistence.load(path)

    # Restore
    recovery = SessionRecovery(persistence)
    restored = recovery.restore_session(data)

    assert restored.session_id == "restore-123"
    assert str(restored.cwd) == "/restore/path"