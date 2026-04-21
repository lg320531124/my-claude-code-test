"""Cache Utils - Caching utilities for performance optimization."""

from __future__ import annotations
import time
import hashlib
import asyncio
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

T = TypeVar('T')


class CachePolicy(Enum):
    """Cache eviction policy."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry."""
    key: str
    value: T
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    size: int = 0  # Approximate size in bytes
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Mark entry as accessed."""
        self.access_count += 1
        self.last_access = time.time()


@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size: int = 1000  # Max entries
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    ttl: Optional[float] = None  # Default TTL in seconds
    policy: CachePolicy = CachePolicy.LRU
    cleanup_interval: float = 60.0  # Cleanup every 60 seconds


class Cache(Generic[T]):
    """In-memory cache with configurable eviction."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._entries: Dict[str, CacheEntry[T]] = {}
        self._lock: Optional[asyncio.Lock] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._hits: int = 0
        self._misses: int = 0

    def _get_lock(self) -> asyncio.Lock:
        """Get lock lazily."""
        if self._lock is None:
            try:
                asyncio.get_running_loop()
                self._lock = asyncio.Lock()
            except RuntimeError:
                self._lock = asyncio.Lock()
        return self._lock

    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired():
            self._misses += 1
            del self._entries[key]
            return None

        entry.touch()
        self._hits += 1
        return entry.value

    async def get_async(self, key: str) -> Optional[T]:
        """Get value from cache async."""
        async with self._get_lock():
            return self.get(key)

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        size: int = 0,
        **metadata,
    ) -> CacheEntry[T]:
        """Set value in cache."""
        use_ttl = ttl if ttl is not None else self.config.ttl

        expires_at = None
        if use_ttl is not None:
            expires_at = time.time() + use_ttl

        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
            size=size,
            metadata=metadata,
        )

        # Check capacity
        self._ensure_capacity(entry)

        self._entries[key] = entry
        return entry

    async def set_async(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        **metadata,
    ) -> CacheEntry[T]:
        """Set value in cache async."""
        async with self._get_lock():
            return self.set(key, value, ttl, **metadata)

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    async def delete_async(self, key: str) -> bool:
        """Delete entry from cache async."""
        async with self._get_lock():
            return self.delete(key)

    def clear(self) -> None:
        """Clear cache."""
        self._entries.clear()
        self._hits = 0
        self._misses = 0

    async def clear_async(self) -> None:
        """Clear cache async."""
        async with self._get_lock():
            self.clear()

    def _ensure_capacity(self, new_entry: CacheEntry[T]) -> None:
        """Ensure cache capacity."""
        # Check size limit
        while len(self._entries) >= self.config.max_size:
            self._evict_one()

        # Check byte limit
        total_bytes = sum(e.size for e in self._entries.values()) + new_entry.size
        while total_bytes > self.config.max_bytes and len(self._entries) > 0:
            self._evict_one()
            total_bytes = sum(e.size for e in self._entries.values()) + new_entry.size

    def _evict_one(self) -> None:
        """Evict one entry based on policy."""
        if not self._entries:
            return

        if self.config.policy == CachePolicy.LRU:
            # Evict least recently accessed
            key = min(self._entries.keys(), key=lambda k: self._entries[k].last_access)
        elif self.config.policy == CachePolicy.LFU:
            # Evict least frequently accessed
            key = min(self._entries.keys(), key=lambda k: self._entries[k].access_count)
        elif self.config.policy == CachePolicy.FIFO:
            # Evict oldest
            key = min(self._entries.keys(), key=lambda k: self._entries[k].created_at)
        elif self.config.policy == CachePolicy.TTL:
            # Evict expired first, then oldest
            expired = [k for k, e in self._entries.items() if e.is_expired()]
            if expired:
                key = expired[0]
            else:
                key = min(self._entries.keys(), key=lambda k: self._entries[k].expires_at or float('inf'))
        else:
            key = next(iter(self._entries.keys()))

        del self._entries[key]

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired = [k for k, e in self._entries.items() if e.is_expired()]
        for key in expired:
            del self._entries[key]
        return len(expired)

    async def cleanup_expired_async(self) -> int:
        """Remove expired entries async."""
        async with self._get_lock():
            return self.cleanup_expired()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0

        return {
            "entries": len(self._entries),
            "total_bytes": sum(e.size for e in self._entries.values()),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "max_size": self.config.max_size,
            "max_bytes": self.config.max_bytes,
        }

    def has(self, key: str) -> bool:
        """Check if key exists."""
        entry = self._entries.get(key)
        if entry is None:
            return False
        if entry.is_expired():
            del self._entries[key]
            return False
        return True

    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self._entries.keys())

    def size(self) -> int:
        """Get number of entries."""
        return len(self._entries)


def compute_key(*args, **kwargs) -> str:
    """Compute cache key from arguments."""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    ttl: Optional[float] = None,
    cache: Optional[Cache] = None,
    key_func: Optional[Callable] = None,
):
    """Decorator for caching function results."""
    use_cache = cache or Cache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Compute key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = compute_key(func.__name__, *args, **kwargs)

            # Check cache
            result = use_cache.get(key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            use_cache.set(key, result, ttl)
            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Compute key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = compute_key(func.__name__, *args, **kwargs)

            # Check cache
            result = await use_cache.get_async(key)
            if result is not None:
                return result

            # Compute and cache
            result = await func(*args, **kwargs)
            await use_cache.set_async(key, result, ttl)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def create_cache(
    max_size: int = 1000,
    ttl: Optional[float] = None,
    policy: CachePolicy = CachePolicy.LRU,
) -> Cache:
    """Create cache with configuration."""
    config = CacheConfig(
        max_size=max_size,
        ttl=ttl,
        policy=policy,
    )
    return Cache(config)


__all__ = [
    "CachePolicy",
    "CacheEntry",
    "CacheConfig",
    "Cache",
    "compute_key",
    "cached",
    "create_cache",
]