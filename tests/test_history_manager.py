"""Tests for history manager."""

import pytest
from pathlib import Path
from src.cc.services.history_manager import (
    HistoryManager,
    HistoryConfig,
    HistoryType,
    HistoryEntry,
)


@pytest.mark.asyncio
async def test_history_manager_init():
    """Test manager initialization."""
    manager = HistoryManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_add_entry():
    """Test adding entry."""
    manager = HistoryManager()

    entry = await manager.add(
        HistoryType.COMMAND,
        "test command"
    )

    assert entry.type == HistoryType.COMMAND
    assert entry.content == "test command"
    assert len(manager._history) == 1


@pytest.mark.asyncio
async def test_add_query():
    """Test adding query."""
    manager = HistoryManager()

    entry = await manager.add(
        HistoryType.QUERY,
        "SELECT * FROM table"
    )

    assert entry.type == HistoryType.QUERY


@pytest.mark.asyncio
async def test_add_error():
    """Test adding error."""
    manager = HistoryManager()

    entry = await manager.add(
        HistoryType.ERROR,
        "Error occurred",
        {"code": "E001"}
    )

    assert entry.type == HistoryType.ERROR
    assert entry.metadata.get("code") == "E001"


@pytest.mark.asyncio
async def test_start_session():
    """Test starting session."""
    manager = HistoryManager()

    await manager.start_session("session_123")
    assert manager._current_session == "session_123"


@pytest.mark.asyncio
async def test_end_session():
    """Test ending session."""
    manager = HistoryManager()

    await manager.start_session("session_123")
    await manager.end_session()

    assert manager._current_session is None


@pytest.mark.asyncio
async def test_get_history():
    """Test getting history."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "cmd1")
    await manager.add(HistoryType.COMMAND, "cmd2")

    history = await manager.get_history()
    assert len(history) == 2


@pytest.mark.asyncio
async def test_get_history_by_type():
    """Test getting history by type."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "cmd")
    await manager.add(HistoryType.ERROR, "err")

    history = await manager.get_history(type=HistoryType.COMMAND)
    assert len(history) == 1


@pytest.mark.asyncio
async def test_search_history():
    """Test searching history."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "test command")
    await manager.add(HistoryType.COMMAND, "other command")

    results = await manager.search("test")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_entry():
    """Test getting specific entry."""
    manager = HistoryManager()

    entry = await manager.add(HistoryType.COMMAND, "test")
    found = await manager.get_entry(entry.id)

    assert found is not None
    assert found.id == entry.id


@pytest.mark.asyncio
async def test_delete_entry():
    """Test deleting entry."""
    manager = HistoryManager()

    entry = await manager.add(HistoryType.COMMAND, "test")
    result = await manager.delete_entry(entry.id)

    assert result is True
    assert len(manager._history) == 0


@pytest.mark.asyncio
async def test_clear_history():
    """Test clearing history."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "cmd1")
    await manager.add(HistoryType.COMMAND, "cmd2")

    count = await manager.clear()
    assert count == 2
    assert len(manager._history) == 0


@pytest.mark.asyncio
async def test_get_stats():
    """Test getting stats."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "cmd")
    await manager.add(HistoryType.ERROR, "err")

    stats = await manager.get_stats()
    assert stats["total_entries"] == 2


@pytest.mark.asyncio
async def test_export_json():
    """Test exporting as JSON."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "test")

    exported = await manager.export("json")
    assert "test" in exported


@pytest.mark.asyncio
async def test_export_text():
    """Test exporting as text."""
    manager = HistoryManager()

    await manager.add(HistoryType.COMMAND, "test")

    exported = await manager.export("text")
    assert "test" in exported


@pytest.mark.asyncio
async def test_history_type_enum():
    """Test history type enum."""
    assert HistoryType.COMMAND.value == "command"
    assert HistoryType.QUERY.value == "query"
    assert HistoryType.ERROR.value == "error"


@pytest.mark.asyncio
async def test_history_config():
    """Test history config."""
    config = HistoryConfig(
        max_entries=500,
        persist=False,
        retention_days=7,
    )

    assert config.max_entries == 500
    assert config.persist is False