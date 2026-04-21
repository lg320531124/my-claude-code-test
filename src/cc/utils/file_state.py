"""File State Cache - Cache file state for quick access."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FileState:
    """Cached file state."""
    path: Path
    exists: bool
    size: int
    modified: datetime
    hash: str
    content_preview: str


class FileStateCache:
    """Cache for file states."""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, FileState] = field(default_factory=dict)
        self._max_size = max_size

    async def get(self, path: Path) -> Optional[FileState]:
        """Get cached state."""
        key = str(path)
        return self._cache.get(key)

    async def update(self, path: Path) -> FileState:
        """Update cached state."""
        import aiofiles
        import hashlib

        key = str(path)

        exists = path.exists()
        size = 0
        modified = datetime.now()
        hash_str = ""
        preview = ""

        if exists:
            stat = path.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime)

            # Hash
            async with aiofiles.open(path, "rb") as f:
                content = await f.read()
                hash_str = hashlib.md5(content).hexdigest()[:16]

            # Preview
            if size < 10000:
                preview = content[:500].decode(errors="replace")

        state = FileState(
            path=path,
            exists=exists,
            size=size,
            modified=modified,
            hash=hash_str,
            content_preview=preview,
        )

        # Manage cache size
        if len(self._cache) >= self._max_size:
            # Remove oldest
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].modified
            )
            self._cache.pop(oldest_key)

        self._cache[key] = state
        return state

    async def invalidate(self, path: Path) -> None:
        """Remove from cache."""
        key = str(path)
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()

    def has_changed(self, path: Path, cached: FileState) -> bool:
        """Check if file changed."""
        if not path.exists():
            return cached.exists

        stat = path.stat()
        return (
            stat.st_size != cached.size or
            stat.st_mtime != cached.modified.timestamp()
        )


# Global cache
_cache: Optional[FileStateCache] = None


def get_file_cache() -> FileStateCache:
    """Get global cache."""
    if _cache is None:
        _cache = FileStateCache()
    return _cache


__all__ = [
    "FileState",
    "FileStateCache",
    "get_file_cache",
]