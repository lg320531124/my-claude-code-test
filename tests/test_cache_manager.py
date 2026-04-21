"""Tests for cache manager."""

import pytest
from src.cc.services.cache_manager import (
    CacheManager,
    CacheConfig,
    CacheType,
    CachePolicy,
)


@pytest.mark.asyncio
async def test_cache_manager_init():
    """Test manager initialization."""
    manager = CacheManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_set_get():
    """Test set and get."""
    manager = CacheManager()

    await manager.set("test_key", "test_value")
    value = await manager.get("test_key")

    assert value == "test_value"


@pytest.mark.asyncio
async def test_get_missing():
    """Test getting missing key."""
    manager = CacheManager()

    value = await manager.get("missing_key")
    assert value is None


@pytest.mark.asyncio
async def test_delete():
    """Test delete."""
    manager = CacheManager()

    await manager.set("test_key", "test_value")
    result = await manager.delete("test_key")

    assert result is True
    value = await manager.get("test_key")
    assert value is None


@pytest.mark.asyncio
async def test_exists():
    """Test exists."""
    manager = CacheManager()

    await manager.set("test_key", "test_value")
    result = await manager.exists("test_key")

    assert result is True


@pytest.mark.asyncio
async def test_clear():
    """Test clear."""
    manager = CacheManager()

    await manager.set("key1", "value1")
    await manager.set("key2", "value2")

    count = await manager.clear()
    assert count == 2


@pytest.mark.asyncio
async def test_ttl_expiration():
    """Test TTL expiration."""
    manager = CacheManager()

    await manager.set("test_key", "test_value", ttl=-1)

    # Should be expired
    value = await manager.get("test_key")
    assert value is None


@pytest.mark.asyncio
async def test_cleanup():
    """Test cleanup."""
    manager = CacheManager()

    # Add expired entry
    await manager.set("expired", "value", ttl=-1)

    count = await manager.cleanup()
    assert count == 1


@pytest.mark.asyncio
async def test_get_or_set():
    """Test get_or_set."""
    manager = CacheManager()

    # Not in cache
    value = await manager.get_or_set(
        "test_key",
        lambda: "computed_value"
    )

    assert value == "computed_value"

    # Now in cache
    value2 = await manager.get_or_set(
        "test_key",
        lambda: "new_value"
    )

    assert value2 == "computed_value"


@pytest.mark.asyncio
async def test_get_stats():
    """Test get stats."""
    manager = CacheManager()

    await manager.set("key1", "value1")

    stats = await manager.get_stats()
    assert stats["total_entries"] == 1


@pytest.mark.asyncio
async def test_get_keys():
    """Test get keys."""
    manager = CacheManager()

    await manager.set("key1", "value1")
    await manager.set("key2", "value2")

    keys = await manager.get_keys()
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_eviction():
    """Test eviction."""
    config = CacheConfig(max_size=2)
    manager = CacheManager(config)

    await manager.set("key1", "value1")
    await manager.set("key2", "value2")
    await manager.set("key3", "value3")

    # One should be evicted
    keys = await manager.get_keys()
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_cache_type_enum():
    """Test cache type enum."""
    assert CacheType.MEMORY.value == "memory"
    assert CacheType.FILE.value == "file"


@pytest.mark.asyncio
async def test_cache_policy_enum():
    """Test cache policy enum."""
    assert CachePolicy.LRU.value == "lru"
    assert CachePolicy.LFU.value == "lfu"


@pytest.mark.asyncio
async def test_cache_config():
    """Test cache config."""
    config = CacheConfig(
        type=CacheType.HYBRID,
        policy=CachePolicy.LFU,
        max_size=50,
    )

    assert config.type == CacheType.HYBRID
    assert config.max_size == 50


@pytest.mark.asyncio
async def test_lru_policy():
    """Test LRU policy."""
    config = CacheConfig(policy=CachePolicy.LRU, max_size=2)
    manager = CacheManager(config)

    await manager.set("a", "1")
    await manager.set("b", "2")
    await manager.get("a")  # Access a
    await manager.set("c", "3")  # Should evict b

    assert await manager.exists("a") is True
    assert await manager.exists("b") is False