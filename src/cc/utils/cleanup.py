"""Cleanup Utils - Async cleanup operations."""

from __future__ import annotations
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class CleanupResult:
    """Cleanup operation result."""
    items_removed: int
    space_freed_mb: float
    errors: List[str]
    duration_ms: float


class CleanupManager:
    """Manage cleanup operations."""

    def __init__(self):
        self._cleanup_handlers: List[Callable] = []
        self._temp_dirs: List[Path] = []

    async def register_handler(self, handler: Callable) -> None:
        """Register cleanup handler."""
        self._cleanup_handlers.append(handler)

    async def run_cleanup(self) -> CleanupResult:
        """Run all cleanup handlers."""
        start_time = asyncio.get_event_loop().time()
        items_removed = 0
        space_freed = 0.0
        errors = []

        for handler in self._cleanup_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler()
                else:
                    result = handler()

                if isinstance(result, dict):
                    items_removed += result.get("items_removed", 0)
                    space_freed += result.get("space_freed_mb", 0)

            except Exception as e:
                errors.append(str(e))

        duration = (asyncio.get_event_loop().time() - start_time) * 1000

        return CleanupResult(
            items_removed=items_removed,
            space_freed_mb=space_freed,
            errors=errors,
            duration_ms=duration,
        )

    async def cleanup_temp_files(self) -> dict:
        """Clean up temporary files."""
        items = 0
        space = 0.0

        # Clean registered temp dirs
        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                try:
                    size = sum(
                        f.stat().st_size
                        for f in temp_dir.rglob("*")
                        if f.is_file()
                    )
                    shutil.rmtree(temp_dir)
                    items += 1
                    space += size / (1024 * 1024)
                except Exception:
                    pass

        self._temp_dirs.clear()

        return {"items_removed": items, "space_freed_mb": space}

    async def cleanup_cache_files(
        self,
        cache_dir: Path,
        max_age_days: int = 7,
    ) -> dict:
        """Clean up old cache files."""
        items = 0
        space = 0.0

        if not cache_dir.exists():
            return {"items_removed": 0, "space_freed_mb": 0}

        now = asyncio.get_event_loop().time()

        for file_path in cache_dir.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                stat = file_path.stat()
                age_seconds = now - stat.st_mtime
                age_days = age_seconds / (24 * 3600)

                if age_days > max_age_days:
                    space += stat.st_size / (1024 * 1024)
                    file_path.unlink()
                    items += 1
            except Exception:
                pass

        return {"items_removed": items, "space_freed_mb": space}

    async def cleanup_empty_dirs(self, root_dir: Path) -> dict:
        """Clean up empty directories."""
        items = 0

        for dir_path in list(root_dir.rglob("*")):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    items += 1
                except Exception:
                    pass

        return {"items_removed": items, "space_freed_mb": 0}

    def track_temp_dir(self, path: Path) -> None:
        """Track a temp directory for cleanup."""
        self._temp_dirs.append(path)


class TempFileManager:
    """Manage temporary files."""

    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(tempfile.gettempdir()) / "claude-code"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._created_files: List[Path] = []

    def create_temp_file(
        self,
        prefix: str = "claude",
        suffix: str = ".tmp",
    ) -> Path:
        """Create temporary file."""
        import uuid
        name = f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
        path = self.base_dir / name
        self._created_files.append(path)
        return path

    def create_temp_dir(self, prefix: str = "claude") -> Path:
        """Create temporary directory."""
        import uuid
        name = f"{prefix}_{uuid.uuid4().hex[:8]}"
        path = self.base_dir / name
        path.mkdir(parents=True, exist_ok=True)
        self._created_files.append(path)
        return path

    async def cleanup(self) -> None:
        """Clean up created files."""
        for path in self._created_files:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.is_file():
                    path.unlink()
            except Exception:
                pass

        self._created_files.clear()

    def get_temp_path(self, name: str) -> Path:
        """Get path in temp directory."""
        return self.base_dir / name


async def cleanup_on_exit() -> None:
    """Run cleanup on exit."""
    manager = CleanupManager()
    await manager.run_cleanup()


def register_cleanup_handler(handler: Callable) -> None:
    """Register cleanup handler."""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = CleanupManager()
    _cleanup_manager.register_handler(handler)


# Global manager
_cleanup_manager: Optional[CleanupManager] = None
_temp_manager: Optional[TempFileManager] = None


def get_cleanup_manager() -> CleanupManager:
    """Get global cleanup manager."""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = CleanupManager()
    return _cleanup_manager


def get_temp_manager() -> TempFileManager:
    """Get global temp manager."""
    global _temp_manager
    if _temp_manager is None:
        _temp_manager = TempFileManager()
    return _temp_manager


__all__ = [
    "CleanupResult",
    "CleanupManager",
    "TempFileManager",
    "cleanup_on_exit",
    "register_cleanup_handler",
    "get_cleanup_manager",
    "get_temp_manager",
]