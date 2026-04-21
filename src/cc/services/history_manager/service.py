"""History Manager - Manage command history."""

from __future__ import annotations
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class HistoryType(Enum):
    """History types."""
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    SESSION = "session"


@dataclass
class HistoryEntry:
    """History entry."""
    type: HistoryType
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    id: str = ""


@dataclass
class HistoryConfig:
    """History configuration."""
    max_entries: int = 1000
    persist: bool = True
    storage_path: Optional[Path] = None
    auto_cleanup: bool = True
    retention_days: int = 30


class HistoryManager:
    """Manage command history."""

    def __init__(self, config: Optional[HistoryConfig] = None):
        self.config = config or HistoryConfig()
        self._history: List[HistoryEntry] = []
        self._current_session: Optional[str] = None

        # Load persisted history
        if self.config.persist and self.config.storage_path:
            self._load_from_file()

    def _load_from_file(self) -> None:
        """Load history from file."""
        if not self.config.storage_path:
            return

        path = self.config.storage_path

        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())

            for entry_data in data.get("entries", []):
                entry = HistoryEntry(
                    type=HistoryType(entry_data["type"]),
                    content=entry_data["content"],
                    timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                    metadata=entry_data.get("metadata", {}),
                    session_id=entry_data.get("session_id"),
                    id=entry_data.get("id", ""),
                )

                self._history.append(entry)

            logger.info(f"Loaded {len(self._history)} history entries")
        except Exception as e:
            logger.error(f"Failed to load history: {e}")

    async def save(self) -> None:
        """Save history to file."""
        if not self.config.persist or not self.config.storage_path:
            return

        path = self.config.storage_path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "entries": [
                    {
                        "type": e.type.value,
                        "content": e.content,
                        "timestamp": e.timestamp.isoformat(),
                        "metadata": e.metadata,
                        "session_id": e.session_id,
                        "id": e.id,
                    }
                    for e in self._history[-self.config.max_entries:]
                ],
            }

            path.write_text(json.dumps(data, indent=2))
            logger.info(f"Saved {len(self._history)} history entries")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    async def add(
        self,
        type: HistoryType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HistoryEntry:
        """Add history entry."""
        import uuid

        entry = HistoryEntry(
            type=type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            session_id=self._current_session,
            id=str(uuid.uuid4())[:8],
        )

        self._history.append(entry)

        # Trim if over limit
        if len(self._history) > self.config.max_entries:
            self._history = self._history[-self.config.max_entries:]

        # Auto save
        if self.config.persist:
            await self.save()

        return entry

    async def start_session(
        self,
        session_id: str
    ) -> None:
        """Start history session."""
        self._current_session = session_id

        await self.add(
            HistoryType.SESSION,
            f"Session started: {session_id}",
            {"action": "start"}
        )

    async def end_session(self) -> None:
        """End history session."""
        if self._current_session:
            await self.add(
                HistoryType.SESSION,
                f"Session ended: {self._current_session}",
                {"action": "end"}
            )

        self._current_session = None

    async def get_history(
        self,
        limit: int = 50,
        type: Optional[HistoryType] = None,
        session_id: Optional[str] = None
    ) -> List[HistoryEntry]:
        """Get history entries."""
        filtered = self._history

        if type:
            filtered = [e for e in filtered if e.type == type]

        if session_id:
            filtered = [e for e in filtered if e.session_id == session_id]

        return filtered[-limit:]

    async def search(
        self,
        query: str,
        limit: int = 20
    ) -> List[HistoryEntry]:
        """Search history."""
        query_lower = query.lower()

        matches = [
            e for e in self._history
            if query_lower in e.content.lower()
        ]

        return matches[-limit:]

    async def get_entry(
        self,
        entry_id: str
    ) -> Optional[HistoryEntry]:
        """Get specific entry."""
        for entry in self._history:
            if entry.id == entry_id:
                return entry

        return None

    async def delete_entry(
        self,
        entry_id: str
    ) -> bool:
        """Delete entry."""
        for i, entry in enumerate(self._history):
            if entry.id == entry_id:
                self._history.pop(i)
                return True

        return False

    async def clear(
        self,
        session_id: Optional[str] = None
    ) -> int:
        """Clear history."""
        if session_id:
            count = sum(1 for e in self._history if e.session_id == session_id)
            self._history = [
                e for e in self._history
                if e.session_id != session_id
            ]
        else:
            count = len(self._history)
            self._history.clear()

        if self.config.persist:
            await self.save()

        return count

    async def cleanup_old(self) -> int:
        """Cleanup old entries."""
        if not self.config.auto_cleanup:
            return 0

        cutoff = datetime.now() - datetime.timedelta(days=self.config.retention_days)

        old_count = sum(1 for e in self._history if e.timestamp < cutoff)

        self._history = [
            e for e in self._history
            if e.timestamp >= cutoff
        ]

        if old_count > 0 and self.config.persist:
            await self.save()

        return old_count

    async def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        by_type: Dict[str, int] = {}

        for entry in self._history:
            key = entry.type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_entries": len(self._history),
            "by_type": by_type,
            "current_session": self._current_session,
        }

    async def export(
        self,
        format: str = "json"
    ) -> str:
        """Export history."""
        if format == "json":
            data = [
                {
                    "type": e.type.value,
                    "content": e.content,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self._history
            ]

            return json.dumps(data, indent=2)

        # Text format
        lines = []

        for e in self._history:
            lines.append(f"[{e.timestamp.isoformat()}] [{e.type.value}] {e.content}")

        return "\n".join(lines)


__all__ = [
    "HistoryType",
    "HistoryEntry",
    "HistoryConfig",
    "HistoryManager",
]