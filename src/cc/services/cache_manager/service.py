"""Cache Manager - Manage data caching."""

from __future__ import annotations
import asyncio
import json
import hashlib
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class CacheType(Enum):
    """Cache types."""
    MEMORY = "memory"
    FILE = "file"
    HYBRID = "hybrid"


class CachePolicy(Enum):
    """Cache policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """Cache entry."""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hits: int = 0
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheConfig:
    """Cache configuration."""
    type: CacheType = CacheType.MEMORY
    policy: CachePolicy = CachePolicy.LRU
    max_size: int = 100
    max_memory: int = 10 * 1024 * 1024  # 10MB
    default_ttl: Optional[float] = None
    persist_path: Optional[Path] = None
    auto_cleanup: bool = True
    cleanup_interval: float = 60.0


class CacheManager:
    """Manage data caching."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._last_cleanup: float = 0.0

        # Load persisted cache
        if self.config.persist_path:
            self._load_from_file()

    def _generate_key(
        self,
        data: Any
    ) -> str:
        """Generate cache key."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    async def get(
        self,
        key: str
    ) -> Optional[Any]:
        """Get cached value."""
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.expires_at and time.time() > entry.expires_at:
            await self.delete(key)
            return None

        # Update hits
        entry.hits += 1

        # Update access order for LRU
        if self.config.policy == CachePolicy.LRU:
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

        return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> bool:
        """Set cached value."""
        # Calculate size
        try:
            size = len(json.dumps(value))
        except:
            size = 0

        # Check capacity
        await self._ensure_capacity(size)

        # Create entry
        use_ttl = ttl or self.config.default_ttl

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=time.time() + use_ttl if use_ttl else None,
            size=size,
        )

        self._cache[key] = entry

        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        # Persist
        if self.config.persist_path:
            await self._persist_entry(key, entry)

        return True

    async def _ensure_capacity(
        self,
        new_size: int
    ) -> None:
        """Ensure cache capacity."""
        # Check count limit
        while len(self._cache) >= self.config.max_size:
            await self._evict_one()

        # Check memory limit
        total_size = sum(e.size for e in self._cache.values())

        while total_size + new_size > self.config.max_memory:
            await self._evict_one()
            total_size = sum(e.size for e in self._cache.values())

    async def _evict_one(self) -> Optional[str]:
        """Evict one entry based on policy."""
        if not self._cache:
            return None

        key_to_evict = None

        if self.config.policy == CachePolicy.LRU:
            # Least recently used
            key_to_evict = self._access_order[0] if self._access_order else None

        elif self.config.policy == CachePolicy.LFU:
            # Least frequently used
            min_hits = min(e.hits for e in self._cache.values())
            for key, entry in self._cache.items():
                if entry.hits == min_hits:
                    key_to_evict = key
                    break

        elif self.config.policy == CachePolicy.FIFO:
            # First in, first out
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
            key_to_evict = oldest_key

        elif self.config.policy == CachePolicy.TTL:
            # Expired first
            now = time.time()
            for key, entry in self._cache.items():
                if entry.expires_at and entry.expires_at < now:
                    key_to_evict = key
                    break

            if not key_to_evict:
                # Fall back to LRU
                key_to_evict = self._access_order[0] if self._access_order else None

        if key_to_evict:
            await self.delete(key_to_evict)
            return key_to_evict

        return None

    async def delete(
        self,
        key: str
    ) -> bool:
        """Delete cached entry."""
        if key not in self._cache:
            return False

        del self._cache[key]

        if key in self._access_order:
            self._access_order.remove(key)

        return True

    async def exists(
        self,
        key: str
    ) -> bool:
        """Check if key exists."""
        if key not in self._cache:
            return False

        entry = self._cache[key]

        if entry.expires_at and time.time() > entry.expires_at:
            await self.delete(key)
            return False

        return True

    async def clear(self) -> int:
        """Clear cache."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()

        return count

    async def cleanup(self) -> int:
        """Cleanup expired entries."""
        now = time.time()
        count = 0

        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.expires_at and entry.expires_at < now
        ]

        for key in expired_keys:
            await self.delete(key)
            count += 1

        self._last_cleanup = now
        return count

    async def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: Optional[float] = None
    ) -> Any:
        """Get or compute and set."""
        value = await self.get(key)

        if value is not None:
            return value

        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        await self.set(key, value, ttl)
        return value

    async def _load_from_file(self) -> None:
        """Load cache from file."""
        if not self.config.persist_path:
            return

        path = self.config.persist_path

        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())

            for key, entry_data in data.items():
                entry = CacheEntry(
                    key=key,
                    value=entry_data["value"],
                    created_at=entry_data.get("created_at", time.time()),
                    expires_at=entry_data.get("expires_at"),
                    hits=entry_data.get("hits", 0),
                    size=entry_data.get("size", 0),
                )

                # Skip expired
                if entry.expires_at and time.time() > entry.expires_at:
                    continue

                self._cache[key] = entry

            logger.info(f"Loaded {len(self._cache)} cache entries")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    async def _persist_entry(
        self,
        key: str,
        entry: CacheEntry
    ) -> None:
        """Persist entry to file."""
        if not self.config.persist_path:
            return

        # Would save to file
        logger.debug(f"Persisting cache entry: {key}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(e.size for e in self._cache.values())
        total_hits = sum(e.hits for e in self._cache.values())

        return {
            "total_entries": len(self._cache),
            "total_size": total_size,
            "total_hits": total_hits,
            "policy": self.config.policy.value,
            "max_size": self.config.max_size,
            "max_memory": self.config.max_memory,
        }

    async def get_keys(self) -> List[str]:
        """Get all keys."""
        return list(self._cache.keys())


__all__ = [
    "CacheType",
    "CachePolicy",
    "CacheEntry",
    "CacheConfig",
    "CacheManager",
]