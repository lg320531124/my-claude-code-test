"""Session Storage - Async session persistence."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

import aiofiles


@dataclass
class SessionMetadata:
    """Session metadata."""
    session_id: str
    created_at: datetime
    updated_at: datetime
    cwd: str
    model: str
    message_count: int
    token_count: int
    tags: List[str] = field(default_factory=list)


@dataclass
class StoredSession:
    """Stored session data."""
    metadata: SessionMetadata
    messages: List[Dict[str, Any]]
    context: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)


class SessionStorage:
    """Async session storage."""

    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path.home() / ".claude" / "sessions"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_session(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
        state: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> Path:
        """Save session to disk."""
        now = datetime.now()

        session_data = {
            "metadata": {
                "session_id": session_id,
                "created_at": metadata.get("created_at", now.isoformat()) if metadata else now.isoformat(),
                "updated_at": now.isoformat(),
                "cwd": metadata.get("cwd", str(Path.cwd())) if metadata else str(Path.cwd()),
                "model": metadata.get("model", "claude-sonnet-4-6") if metadata else "claude-sonnet-4-6",
                "message_count": len(messages),
                "token_count": metadata.get("token_count", 0) if metadata else 0,
                "tags": metadata.get("tags", []) if metadata else [],
            },
            "messages": messages,
            "context": context or {},
            "state": state or {},
        }

        file_path = self.storage_dir / f"{session_id}.json"

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(session_data, indent=2))

        return file_path

    async def load_session(self, session_id: str) -> Optional[StoredSession]:
        """Load session from disk."""
        file_path = self.storage_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()

        data = json.loads(content)

        metadata = SessionMetadata(
            session_id=data["metadata"]["session_id"],
            created_at=datetime.fromisoformat(data["metadata"]["created_at"]),
            updated_at=datetime.fromisoformat(data["metadata"]["updated_at"]),
            cwd=data["metadata"]["cwd"],
            model=data["metadata"]["model"],
            message_count=data["metadata"]["message_count"],
            token_count=data["metadata"]["token_count"],
            tags=data["metadata"].get("tags", []),
        )

        return StoredSession(
            metadata=metadata,
            messages=data["messages"],
            context=data.get("context", {}),
            state=data.get("state", {}),
        )

    async def list_sessions(
        self,
        limit: int = 50,
        sort_by: str = "updated_at",
    ) -> List[SessionMetadata]:
        """List all sessions."""
        sessions = []

        for file_path in self.storage_dir.glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()

                data = json.loads(content)
                metadata = data.get("metadata", {})

                sessions.append(SessionMetadata(
                    session_id=metadata.get("session_id", file_path.stem),
                    created_at=datetime.fromisoformat(metadata.get("created_at", now.isoformat())),
                    updated_at=datetime.fromisoformat(metadata.get("updated_at", now.isoformat())),
                    cwd=metadata.get("cwd", ""),
                    model=metadata.get("model", ""),
                    message_count=metadata.get("message_count", 0),
                    token_count=metadata.get("token_count", 0),
                    tags=metadata.get("tags", []),
                ))
            except Exception:
                pass

        # Sort
        reverse = sort_by in ["updated_at", "created_at"]
        sessions.sort(
            key=lambda s: getattr(s, sort_by),
            reverse=reverse,
        )

        return sessions[:limit]

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        file_path = self.storage_dir / f"{session_id}.json"

        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    async def search_sessions(
        self,
        query: str,
        tags: List[str] = None,
    ) -> List[SessionMetadata]:
        """Search sessions."""
        all_sessions = await self.list_sessions(limit=1000)

        results = []

        for session in all_sessions:
            # Check tags
            if tags and not any(t in session.tags for t in tags):
                continue

            # Check query in cwd
            if query and query.lower() not in session.cwd.lower():
                continue

            results.append(session)

        return results

    async def get_session_count(self) -> int:
        """Get total session count."""
        return len(list(self.storage_dir.glob("*.json")))

    async def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Clean up old sessions."""
        now = datetime.now()
        deleted = 0

        for file_path in self.storage_dir.glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()

                data = json.loads(content)
                updated_at = datetime.fromisoformat(data["metadata"].get("updated_at", ""))

                age_days = (now - updated_at).days

                if age_days > max_age_days:
                    file_path.unlink()
                    deleted += 1
            except Exception:
                pass

        return deleted


# Global storage
_storage: Optional[SessionStorage] = None

now = datetime.now()


def get_session_storage() -> SessionStorage:
    """Get global session storage."""
    global _storage
    if _storage is None:
        _storage = SessionStorage()
    return _storage


async def save_current_session(
    session_id: str,
    messages: List[Dict[str, Any]],
    **kwargs,
) -> Path:
    """Save current session."""
    storage = get_session_storage()
    return await storage.save_session(session_id, messages, **kwargs)


async def load_session(session_id: str) -> Optional[StoredSession]:
    """Load session."""
    storage = get_session_storage()
    return await storage.load_session(session_id)


__all__ = [
    "SessionMetadata",
    "StoredSession",
    "SessionStorage",
    "get_session_storage",
    "save_current_session",
    "load_session",
]