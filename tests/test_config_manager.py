"""Tests for config manager."""

import pytest
from pathlib import Path
from src.cc.services.config_manager import (
    ConfigManager,
    ConfigManagerConfig,
    ConfigSource,
    ConfigPriority,
)


@pytest.mark.asyncio
async def test_config_manager_init():
    """Test manager initialization."""
    manager = ConfigManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_get_default():
    """Test getting default config."""
    manager = ConfigManager()

    value = await manager.get("model")
    assert value is not None


@pytest.mark.asyncio
async def test_get_unknown():
    """Test getting unknown config."""
    manager = ConfigManager()

    value = await manager.get("unknown", default="default")
    assert value == "default"


@pytest.mark.asyncio
async def test_set_config():
    """Test setting config."""
    manager = ConfigManager()

    result = await manager.set("model", "claude-opus-4-7")
    assert result is True

    value = await manager.get("model")
    assert value == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_get_all():
    """Test getting all config."""
    manager = ConfigManager()

    all_config = await manager.get_all()
    assert len(all_config) > 0


@pytest.mark.asyncio
async def test_delete_config():
    """Test deleting config."""
    manager = ConfigManager()

    await manager.set("custom_key", "value")
    result = await manager.delete("custom_key")

    assert result is True


@pytest.mark.asyncio
async def test_reset_config():
    """Test resetting config."""
    manager = ConfigManager()

    await manager.set("model", "custom_model")
    await manager.reset("model")

    value = await manager.get("model")
    assert value == ConfigManager.DEFAULTS["model"]


@pytest.mark.asyncio
async def test_reset_all():
    """Test resetting all config."""
    manager = ConfigManager()

    await manager.set("model", "custom")
    await manager.reset_all()

    value = await manager.get("model")
    assert value == ConfigManager.DEFAULTS["model"]


@pytest.mark.asyncio
async def test_watch_config():
    """Test watching config."""
    manager = ConfigManager()

    changes = []

    async def watcher(key, old, new):
        changes.append((key, old, new))

    await manager.watch("model", watcher)
    await manager.set("model", "new_model")

    assert len(changes) == 1


@pytest.mark.asyncio
async def test_export_import():
    """Test export/import."""
    manager = ConfigManager()

    exported = await manager.export()
    assert exported is not None

    count = await manager.import_config(exported)
    assert count > 0


@pytest.mark.asyncio
async def test_get_stats():
    """Test getting stats."""
    manager = ConfigManager()

    stats = await manager.get_stats()
    assert stats["total_entries"] > 0


@pytest.mark.asyncio
async def test_get_by_source():
    """Test getting by source."""
    manager = ConfigManager()

    defaults = await manager.get_by_source(ConfigSource.DEFAULT)
    assert len(defaults) > 0


@pytest.mark.asyncio
async def test_config_source_enum():
    """Test config source enum."""
    assert ConfigSource.DEFAULT.value == "default"
    assert ConfigSource.FILE.value == "file"
    assert ConfigSource.ENV.value == "env"


@pytest.mark.asyncio
async def test_config_priority_enum():
    """Test config priority enum."""
    assert ConfigPriority.LOWEST.value == 0
    assert ConfigPriority.HIGHEST.value == 100


@pytest.mark.asyncio
async def test_config_manager_config():
    """Test config manager config."""
    config = ConfigManagerConfig(
        env_prefix="MY_APP_",
        auto_reload=True,
    )

    assert config.env_prefix == "MY_APP_"


@pytest.mark.asyncio
async def test_validate():
    """Test validation."""
    manager = ConfigManager()

    # No validators by default
    result = await manager.validate("model", "any_value")
    assert result is True


@pytest.mark.asyncio
async def test_add_validator():
    """Test adding validator."""
    manager = ConfigManager()

    def is_string(v):
        return isinstance(v, str)

    result = await manager.add_validator("model", is_string)
    assert result is True