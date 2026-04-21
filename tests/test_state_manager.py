"""Tests for state manager."""

import pytest
from src.cc.services.state_manager import (
    StateManager,
    StateConfig,
    StateScope,
    StateType,
)


@pytest.mark.asyncio
async def test_state_manager_init():
    """Test manager initialization."""
    manager = StateManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_get_set():
    """Test get and set."""
    manager = StateManager()

    await manager.set("test_key", "test_value")
    value = await manager.get("test_key")

    assert value == "test_value"


@pytest.mark.asyncio
async def test_get_default():
    """Test get with default."""
    manager = StateManager()

    value = await manager.get("nonexistent", default="default")
    assert value == "default"


@pytest.mark.asyncio
async def test_delete():
    """Test delete."""
    manager = StateManager()

    await manager.set("test_key", "test_value")
    result = await manager.delete("test_key")

    assert result is True
    value = await manager.get("test_key")
    assert value is None


@pytest.mark.asyncio
async def test_exists():
    """Test exists."""
    manager = StateManager()

    await manager.set("test_key", "test_value")
    result = await manager.exists("test_key")

    assert result is True


@pytest.mark.asyncio
async def test_clear():
    """Test clear."""
    manager = StateManager()

    await manager.set("key1", "value1")
    await manager.set("key2", "value2")

    count = await manager.clear()
    assert count == 2


@pytest.mark.asyncio
async def test_get_all():
    """Test get all."""
    manager = StateManager()

    await manager.set("key1", "value1")
    await manager.set("key2", "value2")

    all_state = await manager.get_all()
    assert len(all_state) == 2


@pytest.mark.asyncio
async def test_get_by_scope():
    """Test get by scope."""
    manager = StateManager()

    await manager.set("global_key", "value", scope=StateScope.GLOBAL)
    await manager.set("session_key", "value", scope=StateScope.SESSION)

    global_state = await manager.get_all(scope=StateScope.GLOBAL)
    assert len(global_state) == 1


@pytest.mark.asyncio
async def test_watch():
    """Test watch."""
    manager = StateManager()

    changes = []

    async def watcher(key, old, new):
        changes.append((key, old, new))

    await manager.watch("test_key", watcher)
    await manager.set("test_key", "value")

    assert len(changes) == 1


@pytest.mark.asyncio
async def test_cleanup():
    """Test cleanup."""
    manager = StateManager()

    # Set with TTL
    await manager.set("temp_key", "value", ttl=-1)

    count = await manager.cleanup()
    assert count == 1


@pytest.mark.asyncio
async def test_get_stats():
    """Test get stats."""
    manager = StateManager()

    await manager.set("key1", "value")
    await manager.set("key2", "value")

    stats = await manager.get_stats()
    assert stats["total_entries"] == 2


@pytest.mark.asyncio
async def test_export():
    """Test export."""
    manager = StateManager()

    await manager.set("test_key", "test_value")

    exported = await manager.export()
    assert "test_key" in exported


@pytest.mark.asyncio
async def test_state_scope_enum():
    """Test state scope enum."""
    assert StateScope.GLOBAL.value == "global"
    assert StateScope.SESSION.value == "session"


@pytest.mark.asyncio
async def test_state_type_enum():
    """Test state type enum."""
    assert StateType.CONFIG.value == "config"
    assert StateType.CACHE.value == "cache"


@pytest.mark.asyncio
async def test_state_config():
    """Test state config."""
    config = StateConfig(
        persist=True,
        max_entries=100,
    )

    assert config.max_entries == 100