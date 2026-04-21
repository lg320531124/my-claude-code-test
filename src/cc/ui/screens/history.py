"""History Screen - Session history browser."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class HistoryEntry:
    """History entry."""
    id: str
    session_id: str
    timestamp: datetime
    cwd: str
    prompt: str = ""
    response: str = ""
    tools_used: List[str] = field(default_factory=list)
    tokens: int = 0
    duration: float = 0.0
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryFilter:
    """History filter."""
    search_query: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    cwd: str = ""
    model: str = ""
    has_tools: bool = False
    min_tokens: int = 0
    limit: int = 100


class HistoryScreen:
    """Session history browser screen."""

    def __init__(self):
        self._entries: List[HistoryEntry] = []
        self._filtered: List[HistoryEntry] = []
        self._current_index: int = 0
        self._filter: HistoryFilter = HistoryFilter()
        self._select_callback: Optional[Callable] = None
        self._storage_path: Optional[Path] = None

    def set_storage_path(self, path: str) -> None:
        """Set history storage path.

        Args:
            path: Storage path
        """
        self._storage_path = Path(path)

    async def load(self) -> int:
        """Load history from storage.

        Returns:
            Number of entries loaded
        """
        if not self._storage_path:
            return 0

        self._entries.clear()

        try:
            import aiofiles
            import json

            for file_path in self._storage_path.glob("*.json"):
                try:
                    async with aiofiles.open(file_path, "r") as f:
                        data = json.loads(await f.read())

                    entry = HistoryEntry(
                        id=data.get("id", file_path.stem),
                        session_id=data.get("session_id", ""),
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                        cwd=data.get("cwd", ""),
                        prompt=data.get("prompt", ""),
                        response=data.get("response", ""),
                        tools_used=data.get("tools_used", []),
                        tokens=data.get("tokens", 0),
                        duration=data.get("duration", 0.0),
                        model=data.get("model", ""),
                        metadata=data.get("metadata", {}),
                    )

                    self._entries.append(entry)

                except Exception:
                    pass

        except Exception:
            pass

        # Sort by timestamp descending
        self._entries.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply filter
        self._apply_filter()

        return len(self._entries)

    def set_filter(self, filter: HistoryFilter) -> None:
        """Set history filter.

        Args:
            filter: Filter to apply
        """
        self._filter = filter
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply current filter."""
        self._filtered = []

        for entry in self._entries:
            # Search query
            if self._filter.search_query:
                query_lower = self._filter.search_query.lower()
                if query_lower not in entry.prompt.lower() and query_lower not in entry.response.lower():
                    continue

            # Date range
            if self._filter.start_date and entry.timestamp < self._filter.start_date:
                continue
            if self._filter.end_date and entry.timestamp > self._filter.end_date:
                continue

            # Working directory
            if self._filter.cwd and self._filter.cwd not in entry.cwd:
                continue

            # Model
            if self._filter.model and entry.model != self._filter.model:
                continue

            # Has tools
            if self._filter.has_tools and not entry.tools_used:
                continue

            # Min tokens
            if entry.tokens < self._filter.min_tokens:
                continue

            self._filtered.append(entry)

        # Limit
        self._filtered = self._filtered[:self._filter.limit]
        self._current_index = 0

    def get_entries(self) -> List[HistoryEntry]:
        """Get filtered entries."""
        return self._filtered

    def get_entry(self, index: int) -> Optional[HistoryEntry]:
        """Get entry by index.

        Args:
            index: Entry index

        Returns:
            HistoryEntry or None
        """
        if 0 <= index < len(self._filtered):
            return self._filtered[index]
        return None

    def get_current(self) -> Optional[HistoryEntry]:
        """Get current entry."""
        return self.get_entry(self._current_index)

    def next(self) -> bool:
        """Move to next entry.

        Returns:
            True if moved
        """
        if self._current_index < len(self._filtered) - 1:
            self._current_index += 1
            return True
        return False

    def prev(self) -> bool:
        """Move to previous entry.

        Returns:
            True if moved
        """
        if self._current_index > 0:
            self._current_index -= 1
            return True
        return False

    def select(self, index: int) -> Optional[HistoryEntry]:
        """Select entry.

        Args:
            index: Entry index

        Returns:
            Selected HistoryEntry
        """
        if 0 <= index < len(self._filtered):
            self._current_index = index
            entry = self._filtered[index]

            if self._select_callback:
                try:
                    self._select_callback(entry)
                except Exception:
                    pass

            return entry
        return None

    def set_select_callback(self, callback: Callable) -> None:
        """Set select callback."""
        self._select_callback = callback

    def search(self, query: str) -> List[HistoryEntry]:
        """Search history.

        Args:
            query: Search query

        Returns:
            Matching entries
        """
        results = []
        query_lower = query.lower()

        for entry in self._entries:
            if (
                query_lower in entry.prompt.lower() or
                query_lower in entry.response.lower() or
                query_lower in entry.cwd.lower() or
                any(query_lower in t.lower() for t in entry.tools_used)
            ):
                results.append(entry)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics.

        Returns:
            Stats dict
        """
        if not self._entries:
            return {}

        total_tokens = sum(e.tokens for e in self._entries)
        total_duration = sum(e.duration for e in self._entries)
        unique_tools = set()
        for e in self._entries:
            unique_tools.update(e.tools_used)

        return {
            "total_entries": len(self._entries),
            "total_tokens": total_tokens,
            "total_duration": total_duration,
            "unique_tools": len(unique_tools),
            "avg_tokens": total_tokens / len(self._entries),
            "avg_duration": total_duration / len(self._entries),
            "first_entry": self._entries[-1].timestamp if self._entries else None,
            "last_entry": self._entries[0].timestamp if self._entries else None,
        }

    def clear(self) -> None:
        """Clear history."""
        self._entries.clear()
        self._filtered.clear()
        self._current_index = 0

    async def delete(self, entry_id: str) -> bool:
        """Delete entry.

        Args:
            entry_id: Entry ID

        Returns:
            True if deleted
        """
        # Remove from list
        self._entries = [e for e in self._entries if e.id != entry_id]
        self._apply_filter()

        # Delete file if storage exists
        if self._storage_path:
            file_path = self._storage_path / f"{entry_id}.json"
            if file_path.exists():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, file_path.unlink)
                    return True
                except Exception:
                    pass

        return True


__all__ = [
    "HistoryEntry",
    "HistoryFilter",
    "HistoryScreen",
]
