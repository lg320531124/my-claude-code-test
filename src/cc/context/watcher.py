"""File Monitor - Watch files for context updates."""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class FileEventType(Enum):
    """File event types."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileEvent:
    """File change event."""
    type: FileEventType
    path: Path
    old_path: Optional[Path] = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class FileWatcher:
    """Watch files for changes using asyncio."""

    def __init__(
        self,
        watch_paths: Optional[List[Path]] = None,
        exclude_patterns: List[str] = None,
        poll_interval: float = 1.0,
    ):
        self.watch_paths = watch_paths or []
        self.exclude_patterns = exclude_patterns or [
            "__pycache__",
            ".git",
            "node_modules",
            "*.pyc",
            ".DS_Store",
        ]
        self.poll_interval = poll_interval

        # State tracking
        self._file_state: Dict[Path, dict] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._callbacks: List[Callable] = []

    def add_path(self, path: Path) -> None:
        """Add path to watch."""
        if path not in self.watch_paths:
            self.watch_paths.append(path)

    def remove_path(self, path: Path) -> None:
        """Remove path from watch."""
        if path in self.watch_paths:
            self.watch_paths.remove(path)

    def add_callback(self, callback: Callable) -> None:
        """Add event callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove event callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def start(self) -> None:
        """Start watching."""
        if self._running:
            return

        self._running = True

        # Initial state snapshot
        await self._snapshot_state()

        # Start watch loop
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop watching."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _snapshot_state(self) -> None:
        """Take initial snapshot."""
        for watch_path in self.watch_paths:
            if watch_path.is_dir():
                for file_path in watch_path.rglob("*"):
                    if file_path.is_file() and not self._should_exclude(file_path):
                        self._file_state[file_path] = await self._get_file_info(file_path)
            elif watch_path.is_file():
                self._file_state[watch_path] = await self._get_file_info(watch_path)

    async def _get_file_info(self, path: Path) -> dict:
        """Get file info."""
        try:
            stat = path.stat()
            return {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "exists": True,
            }
        except OSError:
            return {"exists": False}

    async def _watch_loop(self) -> None:
        """Main watch loop."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                events = await self._check_changes()

                for event in events:
                    await self._notify_callbacks(event)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.poll_interval * 2)

    async def _check_changes(self) -> List[FileEvent]:
        """Check for file changes."""
        events = []

        # Check existing files
        for path, old_info in list(self._file_state.items()):
            if old_info.get("exists"):
                new_info = await self._get_file_info(path)

                if not new_info.get("exists"):
                    # File deleted
                    events.append(FileEvent(
                        type=FileEventType.DELETED,
                        path=path,
                    ))
                    del self._file_state[path]

                elif new_info["mtime"] > old_info["mtime"]:
                    # File modified
                    events.append(FileEvent(
                        type=FileEventType.MODIFIED,
                        path=path,
                        metadata={"old_size": old_info["size"], "new_size": new_info["size"]},
                    ))
                    self._file_state[path] = new_info

        # Check for new files
        for watch_path in self.watch_paths:
            if watch_path.is_dir():
                for file_path in watch_path.rglob("*"):
                    if file_path.is_file() and not self._should_exclude(file_path):
                        if file_path not in self._file_state:
                            # New file
                            self._file_state[file_path] = await self._get_file_info(file_path)
                            events.append(FileEvent(
                                type=FileEventType.CREATED,
                                path=file_path,
                            ))

        return events

    async def _notify_callbacks(self, event: FileEvent) -> None:
        """Notify callbacks of event."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception:
                pass

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str or path.match(pattern):
                return True
        return False


class ContextUpdater:
    """Updates context based on file changes."""

    def __init__(self, context_collector: Any):
        self.context_collector = context_collector
        self.watcher = FileWatcher()
        self.last_update: float = 0
        self.update_interval: float = 5.0  # Min seconds between updates
        self._pending_updates: set[Path] = set()

    async def start(self, cwd: Path) -> None:
        """Start watching."""
        self.watcher.add_path(cwd)
        self.watcher.add_callback(self._on_file_change)
        await self.watcher.start()

    async def stop(self) -> None:
        """Stop watching."""
        await self.watcher.stop()

    async def _on_file_change(self, event: FileEvent) -> None:
        """Handle file change."""
        self._pending_updates.add(event.path)

        # Throttle updates
        if time.time() - self.last_update >= self.update_interval:
            await self._apply_updates()

    async def _apply_updates(self) -> None:
        """Apply pending updates."""
        if not self._pending_updates:
            return

        self.last_update = time.time()

        # Collect new context
        list(self._pending_updates)
        self._pending_updates.clear()

        # Could trigger context refresh
        # For now, just track changes

    def get_pending_changes(self) -> List[Path]:
        """Get pending changes."""
        return list(self._pending_updates)


class ProjectStructure:
    """Analyze project structure."""

    def __init__(self, cwd: Path):
        self.cwd = cwd

    async def analyze(self) -> dict:
        """Analyze project structure."""
        return {
            "type": await self._detect_project_type(),
            "files": await self._count_files(),
            "structure": await self._get_structure(),
            "dependencies": await self._get_dependencies(),
            "entry_points": await self._find_entry_points(),
        }

    async def _detect_project_type(self) -> str:
        """Detect project type."""
        checks = [
            ("pyproject.toml", "python"),
            ("setup.py", "python"),
            ("package.json", "javascript"),
            ("Cargo.toml", "rust"),
            ("go.mod", "go"),
            ("pom.xml", "java"),
            ("requirements.txt", "python"),
        ]

        for file, type in checks:
            if (self.cwd / file).exists():
                return type

        return "unknown"

    async def _count_files(self) -> dict:
        """Count files by type."""
        counts = {}

        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(None, lambda: list(self.cwd.rglob("*")))

        for file in files:
            if file.is_file() and not self._should_skip(file):
                ext = file.suffix or "no_ext"
                counts[ext] = counts.get(ext, 0) + 1

        return counts

    async def _get_structure(self) -> dict:
        """Get directory structure."""
        structure = {}

        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, lambda: list(self.cwd.iterdir()))

        for item in items:
            if item.is_dir() and not item.name.startswith("."):
                structure[item.name] = {
                    "type": "directory",
                    "files": len(list(item.glob("*"))),
                }
            elif item.is_file():
                structure[item.name] = {
                    "type": "file",
                    "size": item.stat().st_size,
                }

        return structure

    async def _get_dependencies(self) -> List[str]:
        """Get project dependencies."""
        deps = []

        # Python - try tomllib (3.11+) or tomli
        pyproject = self.cwd / "pyproject.toml"
        if pyproject.exists():
            try:
                # Python 3.11+
                import tomllib
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                    deps.extend(data.get("project", {}).get("dependencies", []))
            except ImportError:
                # Python 3.9/3.10 - try tomli
                try:
                    import tomli
                    with open(pyproject, "rb") as f:
                        data = tomli.load(f)
                        deps.extend(data.get("project", {}).get("dependencies", []))
                except ImportError:
                    pass
            except Exception:
                pass

        # JavaScript
        package_json = self.cwd / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    deps.extend(data.get("dependencies", {}).keys())
                    deps.extend(data.get("devDependencies", {}).keys())
            except Exception:
                pass

        return deps

    async def _find_entry_points(self) -> List[str]:
        """Find entry points."""
        entries = []

        # Common entry files
        entry_files = [
            "main.py", "app.py", "__main__.py", "cli.py",
            "index.js", "index.ts", "app.js", "server.js",
            "main.go", "cmd/main.go",
            "src/main.rs",
        ]

        for file in entry_files:
            path = self.cwd / file
            if path.exists():
                entries.append(file)

        return entries

    def _should_skip(self, path: Path) -> bool:
        """Should skip path."""
        skip_dirs = {"__pycache__", ".git", "node_modules", "venv", ".venv", "dist", "build"}
        return any(d in path.parts for d in skip_dirs)


# Global watcher
_file_watcher: Optional[FileWatcher] = None


def get_file_watcher() -> FileWatcher:
    """Get global file watcher."""
    global _file_watcher
    if _file_watcher is None:
        _file_watcher = FileWatcher()
    return _file_watcher


async def start_file_watching(cwd: Path) -> None:
    """Start file watching."""
    watcher = get_file_watcher()
    watcher.add_path(cwd)
    await watcher.start()


async def stop_file_watching() -> None:
    """Stop file watching."""
    if _file_watcher:
        await _file_watcher.stop()
