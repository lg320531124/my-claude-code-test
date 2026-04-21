"""File History - Track file change history."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class FileHistoryEntry:
    """File history entry."""
    path: str
    timestamp: datetime
    action: str  # created, modified, deleted, read
    content_preview: str = ""
    diff_preview: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileHistory:
    """Track file change history."""

    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self._history: List[...] = field(default_factory=list)
        self._path_history: Dict[str, List[FileHistoryEntry]] = {}

    async def record(self, path: Path, action: str, content: str = None, diff: str = None) -> FileHistoryEntry:
        """Record file action."""
        entry = FileHistoryEntry(
            path=str(path),
            timestamp=datetime.now(),
            action=action,
            content_preview=content[:500] if content else "",
            diff_preview=diff[:500] if diff else "",
        )

        self._history.append(entry)

        # Path-specific history
        path_key = str(path)
        if path_key not in self._path_history:
            self._path_history[path_key] = []
        self._path_history[path_key].append(entry)

        # Manage size
        if len(self._history) > self.max_entries:
            removed = self._history.pop(0)
            if removed.path in self._path_history:
                self._path_history[removed.path] = [
                    e for e in self._path_history[removed.path] if e != removed
                ]

        return entry

    async def get_history(self, path: Path = None) -> List[FileHistoryEntry]:
        """Get history."""
        if path:
            return self._path_history.get(str(path), [])
        return self._history

    async def get_last_action(self, path: Path) -> Optional[FileHistoryEntry]:
        """Get last action for path."""
        history = self._path_history.get(str(path), [])
        return history[-1] if history else None

    async def undo_available(self, path: Path) -> bool:
        """Check if undo is available."""
        history = self._path_history.get(str(path), [])
        if not history:
            return False

        last = history[-1]
        return last.action in ("modified", "created")

    async def get_diff_history(self, path: Path) -> List[str]:
        """Get diff history."""
        history = self._path_history.get(str(path), [])
        return [e.diff_preview for e in history if e.diff_preview]

    def clear(self) -> None:
        """Clear history."""
        self._history.clear()
        self._path_history.clear()


# Global history
_history: Optional[FileHistory] = None


def get_file_history() -> FileHistory:
    """Get global file history."""
    if _history is None:
        _history = FileHistory()
    return _history


__all__ = [
    "FileHistoryEntry",
    "FileHistory",
    "get_file_history",
]