"""Hook History - Async history search."""

from __future__ import annotations
import asyncio
import re
from typing import Dict, Any, Optional, List, Callable, AsyncIterator
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import aiofiles


class HistoryType(Enum):
    """History types."""
    COMMAND = "command"
    QUERY = "query"
    FILE = "file"
    SEARCH = "search"


@dataclass
class HistoryEntry:
    """History entry."""
    id: str
    type: HistoryType
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """History search result."""
    entry: HistoryEntry
    score: float
    match_type: str  # "exact", "prefix", "fuzzy", "regex"


class HistoryManager:
    """Async history manager."""

    def __init__(self, history_dir: Path = None):
        self.history_dir = history_dir or Path.home() / ".claude" / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[HistoryType, List[HistoryEntry]] = {}
        self._search_index: Dict[str, List[str]] = {}

    async def add_entry(
        self,
        type: HistoryType,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> HistoryEntry:
        """Add history entry."""
        import uuid
        entry = HistoryEntry(
            id=uuid.uuid4().hex[:8],
            type=type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        # Add to cache
        if type not in self._cache:
            self._cache[type] = []
        self._cache[type].append(entry)

        # Update search index
        self._update_index(entry)

        # Save to file
        await self._save_entry(entry)

        return entry

    async def get_history(
        self,
        type: HistoryType,
        limit: int = 100,
    ) -> List[HistoryEntry]:
        """Get history by type."""
        if type not in self._cache:
            await self._load_history(type)

        entries = self._cache.get(type, [])
        return entries[-limit:]

    async def search(
        self,
        query: str,
        type: HistoryType = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Search history."""
        results = []

        # Determine which histories to search
        types_to_search = [type] if type else list(HistoryType)

        for h_type in types_to_search:
            entries = await self.get_history(h_type)

            for entry in entries:
                result = self._match_entry(entry, query)
                if result:
                    results.append(result)

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _match_entry(self, entry: HistoryEntry, query: str) -> Optional[SearchResult]:
        """Match entry against query."""
        content = entry.content.lower()
        query_lower = query.lower()

        # Exact match
        if content == query_lower:
            return SearchResult(entry=entry, score=100.0, match_type="exact")

        # Prefix match
        if content.startswith(query_lower):
            score = 80.0 + (len(query) / len(content)) * 20
            return SearchResult(entry=entry, score=score, match_type="prefix")

        # Contains match
        if query_lower in content:
            score = 50.0 + (len(query) / len(content)) * 30
            return SearchResult(entry=entry, score=score, match_type="contains")

        # Regex match
        try:
            if re.search(query, content, re.IGNORECASE):
                return SearchResult(entry=entry, score=40.0, match_type="regex")
        except re.error:
            pass

        return None

    def _update_index(self, entry: HistoryEntry) -> None:
        """Update search index."""
        words = re.findall(r"\w+", entry.content.lower())

        for word in words:
            if word not in self._search_index:
                self._search_index[word] = []
            self._search_index[word].append(entry.id)

    async def _save_entry(self, entry: HistoryEntry) -> None:
        """Save entry to file."""
        file_path = self.history_dir / f"{entry.type.value}.jsonl"

        data = {
            "id": entry.id,
            "type": entry.type.value,
            "content": entry.content,
            "timestamp": entry.timestamp.isoformat(),
            "metadata": entry.metadata,
        }

        async with aiofiles.open(file_path, "a") as f:
            await f.write(json.dumps(data) + "\n")

    async def _load_history(self, type: HistoryType) -> None:
        """Load history from file."""
        import json
        file_path = self.history_dir / f"{type.value}.jsonl"

        if not file_path.exists():
            self._cache[type] = []
            return

        entries = []

        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()

        for line in content.strip().split("\n"):
            if not line:
                continue

            try:
                data = json.loads(line)
                entry = HistoryEntry(
                    id=data["id"],
                    type=HistoryType(data["type"]),
                    content=data["content"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    metadata=data.get("metadata", {}),
                )
                entries.append(entry)
            except Exception:
                pass

        self._cache[type] = entries

    async def clear_history(self, type: HistoryType = None) -> int:
        """Clear history."""
        cleared = 0

        if type:
            if type in self._cache:
                cleared = len(self._cache[type])
                self._cache[type] = []

            file_path = self.history_dir / f"{type.value}.jsonl"
            if file_path.exists():
                file_path.unlink()
        else:
            for t in HistoryType:
                if t in self._cache:
                    cleared += len(self._cache[t])
                self._cache[t] = []

                file_path = self.history_dir / f"{t.value}.jsonl"
                if file_path.exists():
                    file_path.unlink()

        self._search_index.clear()
        return cleared


class HistoryHooks:
    """Hooks for history system."""

    def __init__(self, manager: HistoryManager):
        self._manager = manager
        self._autocomplete_enabled: bool = True

    async def pre_command(self, command: str) -> None:
        """Hook before command execution."""
        # Record command
        await self._manager.add_entry(
            HistoryType.COMMAND,
            command,
        )

    async def pre_query(self, query: str) -> None:
        """Hook before query."""
        # Record query
        await self._manager.add_entry(
            HistoryType.QUERY,
            query,
        )

    async def get_suggestions(self, partial: str) -> List[str]:
        """Get autocomplete suggestions."""
        if not self._autocomplete_enabled:
            return []

        results = await self._manager.search(partial, limit=10)

        return [r.entry.content for r in results]


import json

# Global manager
_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """Get global history manager."""
    global _manager
    if _manager is None:
        _manager = HistoryManager()
    return _manager


__all__ = [
    "HistoryType",
    "HistoryEntry",
    "SearchResult",
    "HistoryManager",
    "HistoryHooks",
    "get_history_manager",
]