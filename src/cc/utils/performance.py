"""Performance Optimization - Async helpers, caching, and token management."""

from __future__ import annotations
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar, Optional, Dict, List
import hashlib
import json


T = TypeVar("T")


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0
    size_bytes: int = 0


class AsyncCache:
    """Async cache with TTL and size limits."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = 3600.0,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
    ):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.max_bytes = max_bytes
        self._current_bytes = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Get lock, creating lazily."""
        if self._lock is None:
            try:
                loop = asyncio.get_running_loop()
                self._lock = asyncio.Lock()
            except RuntimeError:
                self._lock = asyncio.Lock()
        return self._lock

    async def get(self, key: str) -> Any | None:
        """Get cached value."""
        async with self._get_lock():
            entry = self.cache.get(key)
            if not entry:
                return None

            # Check expiry
            if time.time() > entry.expires_at:
                await self._remove_entry(key)
                return None

            entry.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set cached value."""
        async with self._get_lock():
            # Calculate size
            size = self._estimate_size(value)

            # Check if we need to evict
            while (
                len(self.cache) >= self.max_size or
                self._current_bytes + size > self.max_bytes
            ):
                await self._evict_oldest()

            # Create entry
            now = time.time()
            expires = now + (ttl or self.ttl)
            entry = CacheEntry(
                value=value,
                created_at=now,
                expires_at=expires,
                size_bytes=size,
            )

            # Remove old if exists
            if key in self.cache:
                await self._remove_entry(key)

            self.cache[key] = entry
            self._current_bytes += size

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        async with self._get_lock():
            if key in self.cache:
                await self._remove_entry(key)
                return True
            return False

    async def clear(self) -> int:
        """Clear all cache."""
        async with self._get_lock():
            count = len(self.cache)
            self.cache.clear()
            self._current_bytes = 0
            return count

    async def _remove_entry(self, key: str) -> None:
        """Remove entry from cache."""
        entry = self.cache.pop(key, None)
        if entry:
            self._current_bytes -= entry.size_bytes

    async def _evict_oldest(self) -> None:
        """Evict oldest entries."""
        if not self.cache:
            return

        # Sort by created_at
        sorted_keys = sorted(
            self.cache.keys(),
            key=lambda k: self.cache[k].created_at,
        )

        # Remove oldest 10%
        to_remove = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:to_remove]:
            await self._remove_entry(key)

    def _estimate_size(self, value: Any) -> int:
        """Estimate value size in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode())
            elif isinstance(value, bytes):
                return len(value)
            else:
                return len(json.dumps(value))
        except Exception:
            return 100  # Default estimate

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_hits = sum(e.hits for e in self.cache.values())
        return {
            "entries": len(self.cache),
            "bytes": self._current_bytes,
            "max_bytes": self.max_bytes,
            "max_size": self.max_size,
            "total_hits": total_hits,
            "ttl": self.ttl,
        }


def cached(
    key_func: Optional[Callable] = None,
    ttl: Optional[float] = None,
):
    """Decorator for caching async function results."""
    cache = AsyncCache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = _generate_key(func.__name__, args, kwargs)

            # Check cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value

            # Execute
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(key, result, ttl)

            return result

        # Add cache access methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear

        return wrapper

    return decorator


def _generate_key(name: str, args: tuple, kwargs: dict) -> str:
    """Generate cache key from arguments."""
    key_data = json.dumps({
        "name": name,
        "args": [str(a) for a in args],
        "kwargs": {k: str(v) for k, v in kwargs.items()},
    }, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


class ParallelExecutor:
    """Execute tasks in parallel with concurrency limit."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active_tasks: set[asyncio.Task] = set()

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get semaphore, creating lazily."""
        if self._semaphore is None:
            try:
                loop = asyncio.get_running_loop()
                self._semaphore = asyncio.Semaphore(self.max_concurrent)
            except RuntimeError:
                self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def execute(
        self,
        tasks: List[Callable],
        fail_fast: bool = False,
    ) -> List[Any]:
        """Execute multiple tasks in parallel."""
        results = []
        errors = []

        async def run_task(task: Callable, idx: int) -> tuple[int, Any, Exception | None]:
            async with self._get_semaphore():
                try:
                    result = await task()
                    return (idx, result, None)
                except Exception as e:
                    return (idx, None, e)

        # Create all tasks
        coros = [run_task(task, i) for i, task in enumerate(tasks)]

        # Run and collect results
        for coro in asyncio.as_completed(coros):
            idx, result, error = await coro
            if error:
                errors.append((idx, error))
                if fail_fast:
                    raise error
            else:
                results.append((idx, result))

        # Sort by index
        results.sort(key=lambda x: x[0])

        return [r for _, r in results]

    async def map(
        self,
        func: Callable,
        items: List[Any],
    ) -> List[Any]:
        """Map function over items in parallel."""
        tasks = [lambda item=item: func(item) for item in items]
        return await self.execute(tasks)

    async def execute_with_progress(
        self,
        tasks: List[Callable],
        progress_callback: Callable,
    ) -> List[Any]:
        """Execute with progress updates."""
        results = [None] * len(tasks)
        completed = 0

        async def run_task(task: Callable, idx: int):
            async with self._get_semaphore():
                result = await task()
                results[idx] = result
                completed += 1
                progress_callback(completed, len(tasks))
                return result

        coros = [run_task(task, i) for i, task in enumerate(tasks)]
        await asyncio.gather(*coros)
        return results


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 20,
    ):
        self.rate = requests_per_second
        self.burst = burst_size
        self._tokens = burst_size
        self._last_update = time.time()
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Get lock, creating lazily."""
        if self._lock is None:
            try:
                loop = asyncio.get_running_loop()
                self._lock = asyncio.Lock()
            except RuntimeError:
                self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self) -> None:
        """Acquire rate limit token."""
        async with self._get_lock():
            now = time.time()

            # Replenish tokens
            elapsed = now - self._last_update
            self._tokens = min(
                self.burst,
                self._tokens + elapsed * self.rate,
            )
            self._last_update = now

            # Wait if no tokens
            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self.rate
                await asyncio.sleep(wait_time)
                self._tokens = 0

            self._tokens -= 1

    async def acquire_batch(self, count: int) -> None:
        """Acquire multiple tokens."""
        for _ in range(count):
            await self.acquire()


class TokenOptimizer:
    """Optimize token usage for messages."""

    def __init__(self, max_tokens: int = 8192):
        self.max_tokens = max_tokens
        self._token_counts: Dict[str, int] = {}

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Simple estimation: ~4 chars per token
        return len(text) // 4

    def optimize_messages(
        self,
        messages: List[dict],
        priority: Optional[List[str]] = None,
    ) -> List[dict]:
        """Optimize message list to fit within limits."""
        total = 0
        optimized = []

        # Priority order: system, recent user/assistant, older messages
        priority = priority or ["system", "user", "assistant"]

        # Sort messages by priority
        sorted_msgs = sorted(
            messages,
            key=lambda m: (
                priority.index(m.get("role", "")) if m.get("role") in priority else 100,
                -messages.index(m),  # Reverse for recent first
            ),
        )

        for msg in sorted_msgs:
            content = msg.get("content", "")
            tokens = self.estimate_tokens(str(content))

            if total + tokens <= self.max_tokens:
                optimized.append(msg)
                total += tokens
            else:
                # Truncate content if it's the last important message
                if msg.get("role") in ["user", "system"]:
                    remaining = self.max_tokens - total
                    if remaining > 100:
                        truncated = self._truncate_content(content, remaining)
                        optimized.append({**msg, "content": truncated})
                        break

        return optimized

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit token limit."""
        max_chars = max_tokens * 4
        if len(content) > max_chars:
            return content[:max_chars - 50] + "\n... [truncated]"
        return content

    def compact_messages(
        self,
        messages: List[dict],
        strategy: str = "summarize",
    ) -> List[dict]:
        """Compact messages using specified strategy."""
        if strategy == "summarize":
            # Summarize older messages
            return self._summarize_old(messages)
        elif strategy == "keep_recent":
            # Keep only recent messages
            return messages[-10:]
        elif strategy == "keep_system":
            # Keep system and recent
            system = [m for m in messages if m.get("role") == "system"]
            recent = messages[-5:]
            return system + recent
        return messages

    def _summarize_old(self, messages: List[dict]) -> List[dict]:
        """Summarize old messages."""
        # Keep recent full messages
        recent = messages[-5:]

        # Create summary of older messages
        older = messages[:-5]
        if older:
            summary = self._create_summary(older)
            return [
                {"role": "system", "content": f"Previous context:\n{summary}"},
            ] + recent

        return recent

    def _create_summary(self, messages: List[dict]) -> str:
        """Create summary of messages."""
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:100]
            parts.append(f"[{role}] {content}")

        return "\n".join(parts)


@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    operation: str
    duration_ms: float
    tokens_used: int = 0
    cache_hit: bool = False
    parallel_count: int = 0
    error: Optional[str] = None


class PerformanceTracker:
    """Track performance metrics."""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self._operation_times: Dict[str, List[float]] = defaultdict(list)

    def record(self, metric: PerformanceMetrics) -> None:
        """Record performance metric."""
        self.metrics.append(metric)
        self._operation_times[metric.operation].append(metric.duration_ms)

    def get_stats(self, operation: Optional[str] = None) -> dict:
        """Get performance statistics."""
        if operation:
            times = self._operation_times.get(operation, [])
            return {
                "operation": operation,
                "count": len(times),
                "avg_ms": sum(times) / len(times) if times else 0,
                "min_ms": min(times) if times else 0,
                "max_ms": max(times) if times else 0,
            }

        # Aggregate stats
        total_metrics = len(self.metrics)
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        errors = sum(1 for m in self.metrics if m.error)

        return {
            "total_operations": total_metrics,
            "cache_hit_rate": cache_hits / total_metrics if total_metrics else 0,
            "error_rate": errors / total_metrics if total_metrics else 0,
            "operations": dict(self._operation_times),
        }

    def clear(self) -> None:
        """Clear metrics."""
        self.metrics.clear()
        self._operation_times.clear()


# Decorator for timing
def timed(operation: str):
    """Decorator to time async operations."""
    tracker = PerformanceTracker()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            error = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration = (time.time() - start) * 1000
                tracker.record(PerformanceMetrics(
                    operation=operation,
                    duration_ms=duration,
                    error=error,
                ))

        wrapper.tracker = tracker
        return wrapper

    return decorator


# Global instances
_cache: Optional[AsyncCache] = None
_executor: Optional[ParallelExecutor] = None
_tracker: Optional[PerformanceTracker] = None


def get_cache() -> AsyncCache:
    """Get global cache."""
    global _cache
    if _cache is None:
        _cache = AsyncCache()
    return _cache


def get_executor() -> ParallelExecutor:
    """Get global executor."""
    global _executor
    if _executor is None:
        _executor = ParallelExecutor()
    return _executor


def get_tracker() -> PerformanceTracker:
    """Get global tracker."""
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker


__all__ = [
    "AsyncCache",
    "CacheEntry",
    "cached",
    "ParallelExecutor",
    "RateLimiter",
    "TokenOptimizer",
    "PerformanceMetrics",
    "PerformanceTracker",
    "timed",
    "get_cache",
    "get_executor",
    "get_tracker",
]
