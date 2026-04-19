"""Tests for permission persistence."""

import pytest
import json
from pathlib import Path
import tempfile
import time

from cc.permissions.persistence import PermissionPersistence, SessionMemory, hash_input
from cc.types.permission import PermissionDecision


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_permission_persistence_init(temp_dir):
    """Test persistence initialization."""
    persistence = PermissionPersistence(temp_dir)
    assert persistence.decisions == {}


def test_permission_persistence_save_load(temp_dir):
    """Test saving and loading decisions."""
    persistence = PermissionPersistence(temp_dir)

    # Save decision
    persistence.save_decision(
        "Bash(ls *)",
        PermissionDecision.ALLOW,
        expires_days=30,
    )

    assert len(persistence.decisions) == 1

    # Create new instance to test load
    persistence2 = PermissionPersistence(temp_dir)
    assert len(persistence2.decisions) == 1


def test_permission_persistence_get_decision(temp_dir):
    """Test getting saved decision."""
    persistence = PermissionPersistence(temp_dir)

    persistence.save_decision("Read", PermissionDecision.ALLOW, expires_days=30)

    decision = persistence.get_decision("Read")
    assert decision == PermissionDecision.ALLOW


def test_permission_persistence_expired(temp_dir):
    """Test expired decisions."""
    persistence = PermissionPersistence(temp_dir)

    # Save with short expiry
    persistence.save_decision(
        "Bash(ls *)",
        PermissionDecision.ALLOW,
        expires_days=-1,  # Already expired
    )

    decision = persistence.get_decision("Bash(ls *)")
    assert decision is None


def test_permission_persistence_clear_expired(temp_dir):
    """Test clearing expired decisions."""
    persistence = PermissionPersistence(temp_dir)

    # Save expired
    persistence.decisions["expired"] = {
        "decision": "allow",
        "timestamp": time.time(),
        "expires": time.time() - 100,  # Expired
    }

    # Save valid
    persistence.decisions["valid"] = {
        "decision": "allow",
        "timestamp": time.time(),
        "expires": time.time() + 1000,
    }

    persistence._save()

    cleared = persistence.clear_expired()
    assert cleared == 1
    assert len(persistence.decisions) == 1


def test_permission_persistence_clear_all(temp_dir):
    """Test clearing all decisions."""
    persistence = PermissionPersistence(temp_dir)

    persistence.save_decision("Read", PermissionDecision.ALLOW)
    persistence.save_decision("Write", PermissionDecision.DENY)

    assert len(persistence.decisions) == 2

    persistence.clear_all()
    assert len(persistence.decisions) == 0


def test_permission_persistence_list(temp_dir):
    """Test listing decisions."""
    persistence = PermissionPersistence(temp_dir)

    persistence.save_decision("Read", PermissionDecision.ALLOW)
    persistence.save_decision("Write", PermissionDecision.DENY)

    decisions = persistence.list_decisions()
    assert len(decisions) == 2


def test_session_memory():
    """Test session memory."""
    memory = SessionMemory()

    memory.set("Bash", "abc123", PermissionDecision.ALLOW)

    decision = memory.get("Bash", "abc123")
    assert decision == PermissionDecision.ALLOW


def test_session_memory_pattern():
    """Test session pattern memory."""
    memory = SessionMemory()

    memory.set_pattern("Read*", PermissionDecision.ALLOW)

    decision = memory.get_pattern("Read*")
    assert decision == PermissionDecision.ALLOW


def test_session_memory_clear():
    """Test clearing session memory."""
    memory = SessionMemory()

    memory.set("Bash", "abc", PermissionDecision.ALLOW)
    memory.set_pattern("Read*", PermissionDecision.ALLOW)

    memory.clear()

    assert memory.get("Bash", "abc") is None
    assert memory.get_pattern("Read*") is None


def test_hash_input_bash():
    """Test hashing bash input."""
    hash1 = hash_input("Bash", {"command": "ls -la"})
    hash2 = hash_input("Bash", {"command": "ls -la"})
    hash3 = hash_input("Bash", {"command": "ls"})

    assert hash1 == hash2  # Same command
    assert hash1 != hash3  # Different command
    assert len(hash1) == 16


def test_hash_input_file():
    """Test hashing file input."""
    hash1 = hash_input("Read", {"file_path": "/tmp/test.txt"})
    hash2 = hash_input("Read", {"file_path": "/tmp/test.txt"})
    hash3 = hash_input("Write", {"file_path": "/tmp/test.txt"})

    assert hash1 == hash2  # Same file, same tool
    assert hash1 != hash3  # Different tool