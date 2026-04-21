"""Tests for Cache Utils."""

import pytest
import asyncio
import time

from cc.utils.cache_utils import (
    CachePolicy,
    CacheEntry,
    CacheConfig,
    Cache,
    compute_key,
    cached,
    create_cache,
)


class TestCachePolicy:
    """Test CachePolicy enum."""

    def test_all_policies(self):
        """Test all cache policies."""
        assert CachePolicy.LRU.value == "lru"
        assert CachePolicy.LFU.value == "lfu"
        assert CachePolicy.FIFO.value == "fifo"
        assert CachePolicy.TTL.value == "ttl"


class TestCacheEntry:
    """Test CacheEntry."""

    def test_create(self):
        """Test creating cache entry."""
        entry = CacheEntry(key="test", value="hello")
        assert entry.key == "test"
        assert entry.value == "hello"
        assert entry.access_count == 0

    def test_is_expired(self):
        """Test expiration check."""
        entry = CacheEntry(key="test", value="hello")
        assert entry.is_expired() is False

        entry.expires_at = time.time() - 1
        assert entry.is_expired() is True

    def test_touch(self):
        """Test touching entry."""
        entry = CacheEntry(key="test", value="hello")
        entry.touch()
        assert entry.access_count == 1

        entry.touch()
        assert entry.access_count == 2


class TestCacheConfig:
    """Test CacheConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = CacheConfig()
        assert config.max_size == 1000
        assert config.policy == CachePolicy.LRU

    def test_custom(self):
        """Test custom configuration."""
        config = CacheConfig(
            max_size=100,
            ttl=60.0,
            policy=CachePolicy.LFU,
        )
        assert config.max_size == 100
        assert config.ttl == 60.0
        assert config.policy == CachePolicy.LFU


class TestCache:
    """Test Cache."""

    def test_init(self):
        """Test initialization."""
        cache = Cache()
        assert cache.config is not None
        assert len(cache._entries) == 0

    def test_set(self):
        """Test setting value."""
        cache = Cache()
        cache.set("key1", "value1")
        assert len(cache._entries) == 1
        assert cache.get("key1") == "value1"

    def test_get(self):
        """Test getting value."""
        cache = Cache()
        cache.set("key1", "value1")
        value = cache.get("key1")
        assert value == "value1"

    def test_get_missing(self):
        """Test getting missing key."""
        cache = Cache()
        value = cache.get("missing")
        assert value is None

    def test_get_expired(self):
        """Test getting expired entry."""
        cache = Cache()
        cache.set("key1", "value1", ttl=0.1)
        time.sleep(0.2)
        value = cache.get("key1")
        assert value is None

    def test_delete(self):
        """Test deleting entry."""
        cache = Cache()
        cache.set("key1", "value1")
        result = cache.delete("key1")
        assert result is True
        assert cache.get("key1") is None

    def test_delete_missing(self):
        """Test deleting missing key."""
        cache = Cache()
        result = cache.delete("missing")
        assert result is False

    def test_clear(self):
        """Test clearing cache."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert len(cache._entries) == 0

    def test_has(self):
        """Test checking if key exists."""
        cache = Cache()
        cache.set("key1", "value1")
        assert cache.has("key1") is True
        assert cache.has("key2") is False

    def test_keys(self):
        """Test getting keys."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        keys = cache.keys()
        assert len(keys) == 2
        assert "key1" in keys

    def test_size(self):
        """Test getting size."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

    def test_max_size_limit(self):
        """Test max size limit."""
        config = CacheConfig(max_size=3)
        cache = Cache(config)
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        assert cache.size() <= 3

    def test_lru_eviction(self):
        """Test LRU eviction."""
        config = CacheConfig(max_size=2, policy=CachePolicy.LRU)
        cache = Cache(config)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.get("key1")  # Access key1
        cache.set("key3", "value3")  # Should evict key2 (least recently used)
        assert cache.has("key1") is True
        assert cache.has("key3") is True

    def test_fifo_eviction(self):
        """Test FIFO eviction."""
        config = CacheConfig(max_size=2, policy=CachePolicy.FIFO)
        cache = Cache(config)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1 (first in)
        assert cache.has("key1") is False
        assert cache.has("key2") is True
        assert cache.has("key3") is True

    def test_cleanup_expired(self):
        """Test cleaning up expired."""
        cache = Cache()
        cache.set("key1", "value1", ttl=0.1)
        cache.set("key2", "value2")  # No TTL
        time.sleep(0.2)
        count = cache.cleanup_expired()
        assert count == 1
        assert cache.has("key2") is True

    def test_get_stats(self):
        """Test getting statistics."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("missing")
        stats = cache.get_stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_ttl_config(self):
        """Test TTL from config."""
        config = CacheConfig(ttl=1.0)
        cache = Cache(config)
        cache.set("key1", "value1")
        entry = cache._entries["key1"]
        assert entry.expires_at is not None

    @pytest.mark.asyncio
    async def test_get_async(self):
        """Test getting value async."""
        cache = Cache()
        cache.set("key1", "value1")
        value = await cache.get_async("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_set_async(self):
        """Test setting value async."""
        cache = Cache()
        await cache.set_async("key1", "value1")
        assert cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_delete_async(self):
        """Test deleting entry async."""
        cache = Cache()
        cache.set("key1", "value1")
        result = await cache.delete_async("key1")
        assert result is True

    @pytest.mark.asyncio
    async def test_clear_async(self):
        """Test clearing cache async."""
        cache = Cache()
        cache.set("key1", "value1")
        await cache.clear_async()
        assert len(cache._entries) == 0


class TestHelperFunctions:
    """Test helper functions."""

    def test_compute_key(self):
        """Test compute_key function."""
        key1 = compute_key("a", "b", c=1)
        key2 = compute_key("a", "b", c=1)
        assert key1 == key2

        key3 = compute_key("a", "b", c=2)
        assert key1 != key3

    def test_cached_decorator(self):
        """Test cached decorator."""
        call_counts = [0]

        @cached()
        def compute(x):
            call_counts[0] += 1
            return x * 2

        result1 = compute(5)
        result2 = compute(5)

        assert result1 == 10
        assert result2 == 10
        assert call_counts[0] == 1  # Only called once due to cache

    def test_cached_decorator_with_ttl(self):
        """Test cached decorator with TTL."""
        call_counts = [0]

        @cached(ttl=0.1)
        def compute(x):
            call_counts[0] += 1
            return x * 2

        compute(5)
        compute(5)
        time.sleep(0.2)
        compute(5)

        assert call_counts[0] == 2  # Called twice after expiry

    def test_cached_decorator_different_args(self):
        """Test cached decorator with different args."""
        call_counts = [0]

        @cached()
        def compute(x):
            call_counts[0] += 1
            return x * 2

        compute(5)
        compute(10)

        assert call_counts[0] == 2  # Both called

    @pytest.mark.asyncio
    async def test_cached_decorator_async(self):
        """Test cached decorator with async function."""
        call_counts = [0]

        @cached()
        async def compute(x):
            call_counts[0] += 1
            return x * 2

        result1 = await compute(5)
        result2 = await compute(5)

        assert result1 == 10
        assert result2 == 10
        assert call_counts[0] == 1

    def test_create_cache(self):
        """Test create_cache function."""
        cache = create_cache(max_size=50, ttl=60.0)
        assert cache.config.max_size == 50
        assert cache.config.ttl == 60.0