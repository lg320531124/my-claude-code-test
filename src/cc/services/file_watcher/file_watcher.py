"""File Watcher Service - Watch files for changes."""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class WatchEventType(Enum):
    """Watch event types."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class WatchEvent:
    """File watch event."""
    path: Path
    event_type: WatchEventType
    timestamp: float
    old_path: Optional[Path] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class WatchConfig:
    """Watch configuration."""
    path: Path
    recursive: bool = True
    patterns: List[str] = field(default_factory=list)
    ignore_patterns: List[str] = field(default_factory=lambda: ["*.pyc", "__pycache__", ".git"])
    debounce_ms: int = 100


class FileWatcherService:
    """Service for watching file changes."""

    def __init__(self):
        self._watchers: Dict[str, WatchConfig] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._watch_task: asyncio.Task | None = None
        self._file_states: Dict[str, dict] = {}
        self._pending_events: Dict[str, WatchEvent] = {}

    def watch(
        self,
        path: Path,
        handler: Callable,
        recursive: bool = True,
        patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
    ) -> str:
        """Register a watch."""
        watch_id = f"watch_{len(self._watchers)}_{int(time.time())}"

        config = WatchConfig(
            path=path,
            recursive=recursive,
            patterns=patterns or ["*"],
            ignore_patterns=ignore_patterns or ["*.pyc", "__pycache__", ".git"],
        )

        self._watchers[watch_id] = config
        self._handlers[watch_id] = [handler]

        # Initialize file state
        self._initialize_state(watch_id, config)

        return watch_id

    def _initialize_state(self, watch_id: str, config: WatchConfig) -> None:
        """Initialize file state for watch."""
        path = config.path

        if path.is_file():
            self._file_states[str(path)] = {
                "exists": True,
                "mtime": path.stat().st_mtime,
                "size": path.stat().st_size,
            }
        elif path.is_dir():
            for file in self._get_files(config):
                self._file_states[str(file)] = {
                    "exists": True,
                    "mtime": file.stat().st_mtime,
                    "size": file.stat().st_size,
                }

    def _get_files(self, config: WatchConfig) -> List[Path]:
        """Get files matching patterns."""
        files = []

        if config.recursive:
            for pattern in config.patterns:
                files.extend(config.path.glob(f"**/{pattern}"))
        else:
            for pattern in config.patterns:
                files.extend(config.path.glob(pattern))

        # Filter ignore patterns
        filtered = []
        for f in files:
            skip = False
            for ignore in config.ignore_patterns:
                if f.match(ignore) or any(p.match(ignore) for p in f.parts):
                    skip = True
                    break
            if not skip:
                filtered.append(f)

        return filtered

    def add_handler(self, watch_id: str, handler: Callable) -> bool:
        """Add handler to existing watch."""
        if watch_id not in self._watchers:
            return False

        self._handlers[watch_id].append(handler)
        return True

    def unwatch(self, watch_id: str) -> bool:
        """Remove a watch."""
        if watch_id not in self._watchers:
            return False

        del self._watchers[watch_id]
        del self._handlers[watch_id]

        return True

    async def start(self) -> None:
        """Start watching."""
        if self._running:
            return

        self._running = True
        self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop watching."""
        self._running = False

        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self) -> None:
        """Watch loop."""
        while self._running:
            await asyncio.sleep(0.5)
            self._check_changes()

    def _check_changes(self) -> None:
        """Check for file changes."""
        for watch_id, config in self._watchers.items():
            files = self._get_files(config)

            # Check for modifications and deletions
            for path_str, state in list(self._file_states.items()):
                path = Path(path_str)
                if not path.exists():
                    if state["exists"]:
                        # Deleted
                        self._emit_event(watch_id, WatchEvent(
                            path=path,
                            event_type=WatchEventType.DELETED,
                            timestamp=time.time(),
                        ))
                        del self._file_states[path_str]

            # Check current files
            for file in files:
                path_str = str(file)
                current_stat = file.stat()
                current_mtime = current_stat.st_mtime
                current_size = current_stat.st_size

                if path_str not in self._file_states:
                    # Created
                    self._emit_event(watch_id, WatchEvent(
                        path=file,
                        event_type=WatchEventType.CREATED,
                        timestamp=time.time(),
                    ))
                    self._file_states[path_str] = {
                        "exists": True,
                        "mtime": current_mtime,
                        "size": current_size,
                    }
                else:
                    old_state = self._file_states[path_str]
                    if old_state["mtime"] != current_mtime or old_state["size"] != current_size:
                        # Modified
                        self._emit_event(watch_id, WatchEvent(
                            path=file,
                            event_type=WatchEventType.MODIFIED,
                            timestamp=time.time(),
                        ))
                        self._file_states[path_str] = {
                            "exists": True,
                            "mtime": current_mtime,
                            "size": current_size,
                        }

    def _emit_event(self, watch_id: str, event: WatchEvent) -> None:
        """Emit event to handlers."""
        handlers = self._handlers.get(watch_id, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass

    def get_watch_ids(self) -> List[str]:
        """Get all watch IDs."""
        return list(self._watchers.keys())

    def get_stats(self) -> dict:
        """Get watcher statistics."""
        return {
            "total_watchers": len(self._watchers),
            "tracked_files": len(self._file_states),
            "running": self._running,
        }


__all__ = [
    "WatchEventType",
    "WatchEvent",
    "WatchConfig",
    "FileWatcherService",
]
