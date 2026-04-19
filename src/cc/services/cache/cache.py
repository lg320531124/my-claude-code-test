"""Cache Service - In-memory and disk caching."""

from __future__ import annotations
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class CacheEntry(BaseModel):
    """Cache entry."""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hits: int = 0
    size_bytes: int = 0


class CacheConfig(BaseModel):
    """Cache configuration."""
    max_entries: int = Field(default=1000, description="Maximum entries in memory cache")
    max_size_mb: float = Field(default=100, description="Maximum cache size in MB")
    ttl_seconds: int = Field(default=3600, description="Default TTL in seconds")
    disk_cache_path: Optional[str] = Field(default=None, description="Path for disk cache")
    enable_disk: bool = Field(default=False, description="Enable disk persistence")


class CacheService:
    """Unified caching service."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._disk_cache_dir: Optional[Path] = None

        if self.config.enable_disk and self.config.disk_cache_path:
            self._disk_cache_dir = Path(self.config.disk_cache_path)
            self._disk_cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Check memory cache
        entry = self._memory_cache.get(key)
        if entry:
            if entry.expires_at and time.time() > entry.expires_at:
                del self._memory_cache[key]
                return None
            entry.hits += 1
            return entry.value

        # Check disk cache
        if self._disk_cache_dir:
            disk_path = self._disk_cache_dir / f"{self._hash_key(key)}.json"
            if disk_path.exists():
                try:
                    data = json.loads(disk_path.read_text())
                    entry = CacheEntry.model_validate(data)
                    if entry.expires_at and time.time() > entry.expires_at:
                        disk_path.unlink()
                        return None
                    # Promote to memory cache
                    self._memory_cache[key] = entry
                    entry.hits += 1
                    return entry.value
                except Exception:
                    pass

        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persist: bool = False,
    ) -> None:
        """Set value in cache."""
        ttl = ttl or self.config.ttl_seconds
        now = time.time()
        expires_at = now + ttl if ttl > 0 else None

        # Estimate size
        try:
            size_bytes = len(json.dumps(value))
        except Exception:
            size_bytes = 100  # Estimate

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=expires_at,
            size_bytes=size_bytes,
        )

        # Add to memory cache
        self._memory_cache[key] = entry

        # Evict if over limit
        self._evict_if_needed()

        # Persist to disk
        if persist and self._disk_cache_dir:
            disk_path = self._disk_cache_dir / f"{self._hash_key(key)}.json"
            disk_path.write_text(entry.model_dump_json())

    def delete(self, key: str) -> bool:
        """Delete from cache."""
        deleted = False

        if key in self._memory_cache:
            del self._memory_cache[key]
            deleted = True

        if self._disk_cache_dir:
            disk_path = self._disk_cache_dir / f"{self._hash_key(key)}.json"
            if disk_path.exists():
                disk_path.unlink()
                deleted = True

        return deleted

    def clear(self) -> int:
        """Clear all cache."""
        count = len(self._memory_cache)
        self._memory_cache.clear()

        if self._disk_cache_dir:
            for f in self._disk_cache_dir.glob("*.json"):
                f.unlink()

        return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(e.size_bytes for e in self._memory_cache.values())
        total_hits = sum(e.hits for e in self._memory_cache.values())

        return {
            "entries": len(self._memory_cache),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "total_hits": total_hits,
            "disk_enabled": self._disk_cache_dir is not None,
            "max_entries": self.config.max_entries,
            "max_size_mb": self.config.max_size_mb,
        }

    def list_entries(self) -> List[CacheEntry]:
        """List all cache entries."""
        return list(self._memory_cache.values())

    def _hash_key(self, key: str) -> str:
        """Hash key for disk storage."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _evict_if_needed(self) -> None:
        """Evict entries if over limit."""
        # Check entry count
        if len(self._memory_cache) > self.config.max_entries:
            # Evict oldest entries with lowest hits
            entries = sorted(
                self._memory_cache.items(),
                key=lambda x: (x[1].created_at, -x[1].hits),
            )
            for key, _ in entries[:len(entries) - self.config.max_entries]:
                del self._memory_cache[key]

        # Check size
        total_size = sum(e.size_bytes for e in self._memory_cache.values())
        max_size_bytes = self.config.max_size_mb * 1024 * 1024
        if total_size > max_size_bytes:
            # Evict largest entries
            entries = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1].size_bytes,
                reverse=True,
            )
            for key, _ in entries:
                del self._memory_cache[key]
                total_size = sum(e.size_bytes for e in self._memory_cache.values())
                if total_size <= max_size_bytes:
                    break


# Singleton
_cache_service: Optional[CacheService] = None


def get_cache_service(config: Optional[CacheConfig] = None) -> CacheService:
    """Get cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(config)
    return _cache_service


def cache_get(key: str) -> Optional[Any]:
    """Convenience cache get."""
    return get_cache_service().get(key)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Convenience cache set."""
    get_cache_service().set(key, value, ttl)


__all__ = [
    "CacheEntry",
    "CacheConfig",
    "CacheService",
    "get_cache_service",
    "cache_get",
    "cache_set",
]