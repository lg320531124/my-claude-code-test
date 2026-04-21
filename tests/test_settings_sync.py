"""Tests for settings sync."""

import pytest
from src.cc.services.settings_sync_v2 import (
    SettingsSync,
    SyncStatus,
    SyncDirection,
)


@pytest.mark.asyncio
async def test_settings_sync_init():
    """Test settings sync initialization."""
    sync = SettingsSync()
    assert sync.config is not None
    assert sync._state is not None


@pytest.mark.asyncio
async def test_get_setting():
    """Test getting setting."""
    sync = SettingsSync()

    await sync.set_setting("test_key", "test_value")
    value = await sync.get_setting("test_key")

    assert value == "test_value"


@pytest.mark.asyncio
async def test_set_setting():
    """Test setting setting."""
    sync = SettingsSync()

    await sync.set_setting("key1", "value1")

    assert sync._local_settings["key1"] == "value1"


@pytest.mark.asyncio
async def test_sync_push():
    """Test push sync."""
    sync = SettingsSync()

    await sync.set_setting("key", "value")
    result = await sync.sync(SyncDirection.PUSH)

    assert "status" in result


@pytest.mark.asyncio
async def test_sync_pull():
    """Test pull sync."""
    sync = SettingsSync()

    result = await sync.sync(SyncDirection.PULL)

    assert "status" in result


@pytest.mark.asyncio
async def test_sync_both():
    """Test bidirectional sync."""
    sync = SettingsSync()

    await sync.set_setting("key", "value")
    result = await sync.sync(SyncDirection.BOTH)

    assert "status" in result


@pytest.mark.asyncio
async def test_apply_remote_settings():
    """Test applying remote settings."""
    sync = SettingsSync()

    remote = {"remote_key": "remote_value"}
    count = await sync.apply_remote_settings(remote)

    assert count == 1
    assert await sync.get_setting("remote_key") == "remote_value"


@pytest.mark.asyncio
async def test_get_all_settings():
    """Test getting all settings."""
    sync = SettingsSync()

    await sync.set_setting("k1", "v1")
    await sync.set_setting("k2", "v2")

    settings = await sync.get_all_settings()

    assert len(settings) == 2


@pytest.mark.asyncio
async def test_get_state():
    """Test getting state."""
    sync = SettingsSync()

    state = await sync.get_state()

    assert state.status == SyncStatus.OFFLINE


@pytest.mark.asyncio
async def test_get_pending_changes():
    """Test getting pending changes."""
    sync = SettingsSync()

    await sync.set_setting("key", "value")
    pending = await sync.get_pending_changes()

    assert len(pending) == 1


@pytest.mark.asyncio
async def test_clear_pending():
    """Test clearing pending."""
    sync = SettingsSync()

    await sync.set_setting("key", "value")
    count = await sync.clear_pending()

    assert count == 1
    assert len(sync._state.pending_changes) == 0


@pytest.mark.asyncio
async def test_import_settings():
    """Test importing settings."""
    sync = SettingsSync()

    new_settings = {"imported_key": "imported_value"}
    count = await sync.import_settings(new_settings)

    assert count == 1


@pytest.mark.asyncio
async def test_reset():
    """Test resetting settings."""
    sync = SettingsSync()

    await sync.set_setting("key", "value")
    await sync.reset()

    assert len(sync._local_settings) == 0


@pytest.mark.asyncio
async def test_disabled_sync():
    """Test disabled sync."""
    from src.cc.services.settings_sync_v2 import SyncConfig

    sync = SettingsSync(SyncConfig(enabled=False))

    result = await sync.sync()

    assert result["status"] == "disabled"


@pytest.mark.asyncio
async def test_change_history():
    """Test change history."""
    sync = SettingsSync()

    await sync.set_setting("k1", "v1")
    await sync.set_setting("k2", "v2")

    history = await sync.get_history()

    assert len(history) == 2