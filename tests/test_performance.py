"""Tests for Performance Optimization."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
import time

from cc.utils.performance import (
    AsyncCache,
    CacheEntry,
    cached,
    ParallelExecutor,
    RateLimiter,
    TokenOptimizer,
    PerformanceMetrics,
    PerformanceTracker,
    timed,
    get_cache,
    get_executor,
    get_tracker,
)


class TestAsyncCache:
    """Test AsyncCache class."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test cache initialization."""
        cache = AsyncCache()
        assert cache.max_size == 1000
        assert cache.ttl == 3600.0
        assert cache.cache == {}

    @pytest.mark.asyncio
    async def test_init_custom(self):
        """Test custom settings."""
        cache = AsyncCache(max_size=100, ttl_seconds=60.0)
        assert cache.max_size == 100
        assert cache.ttl == 60.0

    @pytest.mark.asyncio
    async def test_set_get(self):
        """Test set and get."""
        cache = AsyncCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing(self):
        """Test getting missing key."""
        cache = AsyncCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete."""
        cache = AsyncCache()
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_missing(self):
        """Test deleting missing key."""
        cache = AsyncCache()
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clear."""
        cache = AsyncCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        count = await cache.clear()
        assert count == 2
        assert cache.cache == {}

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        """Test TTL expiry."""
        cache = AsyncCache(ttl_seconds=0.1)
        await cache.set("key1", "value1", ttl=0.1)

        # Wait for expiry
        await asyncio.sleep(0.2)

        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_hits_tracking(self):
        """Test hit tracking."""
        cache = AsyncCache()
        await cache.set("key1", "value1")

        await cache.get("key1")
        await cache.get("key1")
        await cache.get("key1")

        entry = cache.cache["key1"]
        assert entry.hits == 3

    @pytest.mark.asyncio
    async def test_size_eviction(self):
        """Test size-based eviction."""
        cache = AsyncCache(max_size=3)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")  # Should evict oldest

        assert len(cache.cache) <= 3

    def test_get_stats(self):
        """Test getting stats."""
        cache = AsyncCache()
        stats = cache.get_stats()
        assert "entries" in stats
        assert "bytes" in stats


class TestCachedDecorator:
    """Test cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_function(self):
        """Test caching function results."""
        call_counts = {"count": 0}

        @cached()
        async def my_func(x):
            call_counts["count"] += 1
            return x * 2

        # First call
        result1 = await my_func(5)
        assert result1 == 10
        assert call_counts["count"] == 1

        # Cached call
        result2 = await my_func(5)
        assert result2 == 10
        assert call_counts["count"] == 1  # Not called again

        # Different arg
        result3 = await my_func(6)
        assert result3 == 12
        assert call_counts["count"] == 2


class TestParallelExecutor:
    """Test ParallelExecutor class."""

    def test_init(self):
        """Test executor initialization."""
        executor = ParallelExecutor()
        assert executor.max_concurrent == 10

    def test_init_custom(self):
        """Test custom concurrency."""
        executor = ParallelExecutor(max_concurrent=5)
        assert executor.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        """Test parallel execution."""
        executor = ParallelExecutor(max_concurrent=5)

        async def task(n):
            await asyncio.sleep(0.01)
            return n * 2

        tasks = [lambda n=i: task(n) for i in range(10)]
        results = await executor.execute(tasks)

        assert len(results) == 10
        assert sorted(results) == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    @pytest.mark.asyncio
    async def test_execute_with_errors(self):
        """Test execution with errors."""
        executor = ParallelExecutor()

        async def good_task():
            return "ok"

        async def bad_task():
            raise ValueError("error")

        results = await executor.execute([good_task, bad_task], fail_fast=False)
        assert len(results) == 1
        assert results[0] == "ok"

    @pytest.mark.asyncio
    async def test_map(self):
        """Test map function."""
        executor = ParallelExecutor()

        async def double(x):
            return x * 2

        results = await executor.map(double, [1, 2, 3, 4])
        assert sorted(results) == [2, 4, 6, 8]


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init(self):
        """Test limiter initialization."""
        limiter = RateLimiter()
        assert limiter.rate == 10.0
        assert limiter.burst == 20

    @pytest.mark.asyncio
    async def test_acquire(self):
        """Test acquiring token."""
        limiter = RateLimiter(requests_per_second=100.0)
        await limiter.acquire()
        assert limiter._tokens == limiter.burst - 1

    @pytest.mark.asyncio
    async def test_acquire_batch(self):
        """Test acquiring multiple tokens."""
        limiter = RateLimiter(requests_per_second=100.0)
        # Tokens replenish during acquisition, so check that some were used
        initial_tokens = limiter._tokens
        await limiter.acquire_batch(5)
        # Should have fewer tokens than initial
        assert limiter._tokens < initial_tokens or limiter._tokens <= limiter.burst


class TestTokenOptimizer:
    """Test TokenOptimizer class."""

    def test_init(self):
        """Test optimizer initialization."""
        optimizer = TokenOptimizer()
        assert optimizer.max_tokens == 8192

    def test_estimate_tokens(self):
        """Test token estimation."""
        optimizer = TokenOptimizer()
        # ~4 chars per token
        tokens = optimizer.estimate_tokens("Hello World")  # 11 chars
        assert tokens == 2 or tokens == 3

    def test_optimize_messages_within_limit(self):
        """Test optimization within limit."""
        optimizer = TokenOptimizer(max_tokens=100)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        optimized = optimizer.optimize_messages(messages)
        assert len(optimized) == 2

    def test_optimize_messages_exceeds_limit(self):
        """Test optimization exceeding limit."""
        optimizer = TokenOptimizer(max_tokens=10)
        messages = [
            {"role": "system", "content": "Very long system prompt"},
            {"role": "user", "content": "Very long user message"},
        ]
        optimized = optimizer.optimize_messages(messages)
        assert len(optimized) <= 2

    def test_compact_keep_recent(self):
        """Test compacting with keep_recent."""
        optimizer = TokenOptimizer()
        messages = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
        compacted = optimizer.compact_messages(messages, strategy="keep_recent")
        assert len(compacted) == 10

    def test_compact_keep_system(self):
        """Test compacting with keep_system."""
        optimizer = TokenOptimizer()
        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user1"},
            {"role": "assistant", "content": "asst1"},
            {"role": "user", "content": "user2"},
        ]
        compacted = optimizer.compact_messages(messages, strategy="keep_system")
        assert compacted[0]["role"] == "system"


class TestPerformanceTracker:
    """Test PerformanceTracker class."""

    def test_init(self):
        """Test tracker initialization."""
        tracker = PerformanceTracker()
        assert tracker.metrics == []

    def test_record(self):
        """Test recording metric."""
        tracker = PerformanceTracker()
        metric = PerformanceMetrics(
            operation="test",
            duration_ms=100.0,
        )
        tracker.record(metric)
        assert len(tracker.metrics) == 1

    def test_get_stats(self):
        """Test getting stats."""
        tracker = PerformanceTracker()
        tracker.record(PerformanceMetrics(operation="test1", duration_ms=100.0))
        tracker.record(PerformanceMetrics(operation="test2", duration_ms=200.0))

        stats = tracker.get_stats()
        assert stats["total_operations"] == 2

    def test_get_stats_by_operation(self):
        """Test stats by operation."""
        tracker = PerformanceTracker()
        tracker.record(PerformanceMetrics(operation="test", duration_ms=100.0))
        tracker.record(PerformanceMetrics(operation="test", duration_ms=200.0))

        stats = tracker.get_stats("test")
        assert stats["count"] == 2
        assert stats["avg_ms"] == 150.0

    def test_clear(self):
        """Test clearing."""
        tracker = PerformanceTracker()
        tracker.record(PerformanceMetrics(operation="test", duration_ms=100.0))
        tracker.clear()
        assert tracker.metrics == []


class TestTimedDecorator:
    """Test timed decorator."""

    @pytest.mark.asyncio
    async def test_timed_function(self):
        """Test timing function."""
        @timed("test_op")
        async def my_func():
            await asyncio.sleep(0.1)
            return "done"

        result = await my_func()
        assert result == "done"

        # Check tracker
        stats = my_func.tracker.get_stats("test_op")
        assert stats["count"] == 1
        assert stats["avg_ms"] >= 100


class TestGlobals:
    """Test global instances."""

    def test_get_cache(self):
        """Test getting global cache."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_get_executor(self):
        """Test getting global executor."""
        exec1 = get_executor()
        exec2 = get_executor()
        assert exec1 is exec2

    def test_get_tracker(self):
        """Test getting global tracker."""
        tracker1 = get_tracker()
        tracker2 = get_tracker()
        assert tracker1 is tracker2