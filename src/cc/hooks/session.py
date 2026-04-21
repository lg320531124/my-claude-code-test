"""Session Hook - Async session management."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import uuid


class SessionState(Enum):
    """Session states."""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    CLOSED = "closed"


@dataclass
class SessionData:
    """Session data."""
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    state: SessionState = SessionState.ACTIVE
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        """Get message count."""
        return len(self.messages)

    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        return (self.updated_at - self.created_at).total_seconds()


class SessionHook:
    """Async session management hook."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._current_session: Optional[SessionData] = None
        self._storage_path: Optional[Path] = None
        self._subscribers: List[Callable] = []
        self._session_id_counter: int = 0

    def set_storage_path(self, path: str) -> None:
        """Set session storage path.

        Args:
            path: Storage directory path
        """
        self._storage_path = Path(path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        messages: List[Dict] = None,
        context: Dict = None,
        metadata: Dict = None,
        parent_id: str = None,
        tags: List[str] = None,
    ) -> SessionData:
        """Create new session.

        Args:
            messages: Initial messages
            context: Session context
            metadata: Additional metadata
            parent_id: Parent session ID
            tags: Session tags

        Returns:
            SessionData
        """
        self._session_id_counter += 1
        session_id = f"session_{self._session_id_counter}_{uuid.uuid4().hex[:8]}"

        session = SessionData(
            id=session_id,
            messages=messages or [],
            context=context or {},
            metadata=metadata or {},
            parent_id=parent_id,
            tags=tags or [],
        )

        self._sessions[session_id] = session
        self._current_session = session

        asyncio.create_task(self._notify_subscribers("create", session))

        return session

    def get(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            SessionData or None
        """
        return self._sessions.get(session_id)

    def get_current(self) -> Optional[SessionData]:
        """Get current session.

        Returns:
            Current SessionData
        """
        return self._current_session

    def set_current(self, session_id: str) -> bool:
        """Set current session.

        Args:
            session_id: Session ID

        Returns:
            True if set
        """
        session = self._sessions.get(session_id)
        if session:
            self._current_session = session
            asyncio.create_task(
                self._notify_subscribers("current_change", session)
            )
            return True
        return False

    def update(
        self,
        session_id: str,
        messages: List[Dict] = None,
        context: Dict = None,
        metadata: Dict = None,
        tags: List[str] = None,
    ) -> bool:
        """Update session.

        Args:
            session_id: Session ID
            messages: New messages
            context: Updated context
            metadata: Updated metadata
            tags: Updated tags

        Returns:
            True if updated
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if messages is not None:
            session.messages = messages
        if context is not None:
            session.context.update(context)
        if metadata is not None:
            session.metadata.update(metadata)
        if tags is not None:
            session.tags = tags

        session.updated_at = datetime.now()

        asyncio.create_task(self._notify_subscribers("update", session))

        return True

    def add_message(
        self,
        session_id: str,
        role: str,
        content: Any,
        metadata: Dict = None,
    ) -> bool:
        """Add message to session.

        Args:
            session_id: Session ID
            role: Message role
            content: Message content
            metadata: Message metadata

        Returns:
            True if added
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        session.messages.append(message)
        session.updated_at = datetime.now()

        asyncio.create_task(
            self._notify_subscribers("message_add", session, message)
        )

        return True

    def clear_messages(self, session_id: str) -> bool:
        """Clear session messages.

        Args:
            session_id: Session ID

        Returns:
            True if cleared
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.messages.clear()
        session.updated_at = datetime.now()

        asyncio.create_task(
            self._notify_subscribers("clear", session)
        )

        return True

    def archive(self, session_id: str) -> bool:
        """Archive session.

        Args:
            session_id: Session ID

        Returns:
            True if archived
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.state = SessionState.ARCHIVED
        session.updated_at = datetime.now()

        asyncio.create_task(
            self._notify_subscribers("archive", session)
        )

        return True

    def delete(self, session_id: str) -> bool:
        """Delete session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted
        """
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)

            if self._current_session and self._current_session.id == session_id:
                self._current_session = None

            asyncio.create_task(
                self._notify_subscribers("delete", session)
            )

            return True
        return False

    def list_sessions(
        self,
        state: SessionState = None,
        tags: List[str] = None,
        limit: int = 100,
    ) -> List[SessionData]:
        """List sessions.

        Args:
            state: Optional state filter
            tags: Optional tags filter
            limit: Maximum results

        Returns:
            List of sessions
        """
        sessions = list(self._sessions.values())

        if state:
            sessions = [s for s in sessions if s.state == state]

        if tags:
            sessions = [
                s for s in sessions
                if any(t in s.tags for t in tags)
            ]

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        return sessions[:limit]

    def search(self, query: str) -> List[SessionData]:
        """Search sessions.

        Args:
            query: Search query

        Returns:
            Matching sessions
        """
        results = []
        query_lower = query.lower()

        for session in self._sessions.values():
            # Search in messages
            for msg in session.messages:
                content = msg.get("content", "")
                if isinstance(content, str) and query_lower in content.lower():
                    results.append(session)
                    break

            # Search in tags
            if any(query_lower in tag.lower() for tag in session.tags):
                results.append(session)

        return results

    async def save(self, session_id: str = None) -> bool:
        """Save session to disk.

        Args:
            session_id: Session ID (None for current)

        Returns:
            True if saved
        """
        if not self._storage_path:
            return False

        session = self._sessions.get(session_id) or self._current_session
        if not session:
            return False

        try:
            file_path = self._storage_path / f"{session.id}.json"

            data = {
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "state": session.state.value,
                "messages": session.messages,
                "context": session.context,
                "metadata": session.metadata,
                "parent_id": session.parent_id,
                "tags": session.tags,
            }

            async with asyncio.Lock():
                import aiofiles
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(json.dumps(data, indent=2))

            return True

        except Exception:
            return False

    async def load(self, session_id: str) -> Optional[SessionData]:
        """Load session from disk.

        Args:
            session_id: Session ID

        Returns:
            SessionData or None
        """
        if not self._storage_path:
            return None

        try:
            file_path = self._storage_path / f"{session_id}.json"

            if not file_path.exists():
                return None

            import aiofiles
            async with aiofiles.open(file_path, "r") as f:
                data = json.loads(await f.read())

            session = SessionData(
                id=data["id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                state=SessionState(data["state"]),
                messages=data["messages"],
                context=data["context"],
                metadata=data["metadata"],
                parent_id=data.get("parent_id"),
                tags=data.get("tags", []),
            )

            self._sessions[session.id] = session
            return session

        except Exception:
            return None

    async def load_all(self) -> int:
        """Load all sessions from storage.

        Returns:
            Number of loaded sessions
        """
        if not self._storage_path:
            return 0

        count = 0
        for file_path in self._storage_path.glob("*.json"):
            session_id = file_path.stem
            if await self.load(session_id):
                count += 1

        return count

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to session events.

        Args:
            callback: Callback function
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> bool:
        """Unsubscribe from events.

        Args:
            callback: Callback to remove

        Returns:
            True if removed
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            return True
        return False

    async def _notify_subscribers(
        self,
        event: str,
        session: SessionData,
        data: Any = None,
    ) -> None:
        """Notify subscribers."""
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event, session, data)
                else:
                    subscriber(event, session, data)
            except Exception:
                pass

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value from current session.

        Args:
            key: Context key
            default: Default value

        Returns:
            Context value
        """
        if self._current_session:
            return self._current_session.context.get(key, default)
        return default

    def set_context(self, key: str, value: Any) -> bool:
        """Set context value in current session.

        Args:
            key: Context key
            value: Value to set

        Returns:
            True if set
        """
        if self._current_session:
            self._current_session.context[key] = value
            self._current_session.updated_at = datetime.now()
            return True
        return False


# Global session hook
_session_hook: Optional[SessionHook] = None


def get_session_hook() -> SessionHook:
    """Get global session hook."""
    global _session_hook
    if _session_hook is None:
        _session_hook = SessionHook()
    return _session_hook


async def use_session() -> Dict[str, Any]:
    """Session hook for hooks module.

    Returns session functions.
    """
    hook = get_session_hook()

    return {
        "create": hook.create,
        "get": hook.get,
        "get_current": hook.get_current,
        "set_current": hook.set_current,
        "update": hook.update,
        "add_message": hook.add_message,
        "clear_messages": hook.clear_messages,
        "archive": hook.archive,
        "delete": hook.delete,
        "list_sessions": hook.list_sessions,
        "search": hook.search,
        "save": hook.save,
        "load": hook.load,
        "load_all": hook.load_all,
        "get_context": hook.get_context,
        "set_context": hook.set_context,
        "subscribe": hook.subscribe,
        "unsubscribe": hook.unsubscribe,
    }


__all__ = [
    "SessionState",
    "SessionData",
    "SessionHook",
    "get_session_hook",
    "use_session",
]