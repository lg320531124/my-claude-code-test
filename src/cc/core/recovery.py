"""Session Recovery - Persist and restore sessions."""

from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable, Optional, List
from dataclasses import dataclass, field, asdict

from ..core.session import Session
from ..core.engine import QueryStats


@dataclass
class SessionMetadata:
    """Session metadata."""
    session_id: str
    cwd: str
    created_at: float
    updated_at: float
    message_count: int
    token_count: int
    model: str
    title: str = ""


@dataclass
class SessionData:
    """Complete session data."""
    metadata: SessionMetadata
    messages: List[dict]
    stats: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)


class SessionPersistence:
    """Manages session persistence."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        max_sessions: int = 50,
    ):
        self.storage_dir = storage_dir or Path.home() / ".claude" / "sessions"
        self.max_sessions = max_sessions
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session, engine_stats: dict = None, config: dict = None) -> Path:
        """Save session to file."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"session_{session.session_id}_{timestamp}.json"
        filepath = self.storage_dir / filename

        # Build metadata - convert datetime to timestamp
        created_at_ts = session.created_at.timestamp() if hasattr(session.created_at, 'timestamp') else session.created_at
        metadata = SessionMetadata(
            session_id=session.session_id,
            cwd=str(session.cwd),
            created_at=created_at_ts,
            updated_at=time.time(),
            message_count=len(session.messages),
            token_count=engine_stats.get("total_tokens", 0) if engine_stats else 0,
            model=config.get("model", "") if config else "",
            title=self._generate_title(session),
        )

        # Build messages
        messages = []
        for msg in session.messages:
            msg_data = {
                "role": msg.role,
                "content": [],
            }
            for block in msg.content:
                if hasattr(block, "model_dump"):
                    msg_data["content"].append(block.model_dump())
                else:
                    msg_data["content"].append({
                        "type": getattr(block, "type", "text"),
                        "text": getattr(block, "text", str(block)),
                    })
            messages.append(msg_data)

        # Build session data
        data = SessionData(
            metadata=metadata,
            messages=messages,
            stats=engine_stats or {},
            config=config or {},
        )

        # Write to file
        with open(filepath, "w") as f:
            json.dump(asdict(data), f, indent=2)

        # Clean up old sessions
        self._cleanup_old_sessions()

        return filepath

    def load(self, filepath: Path) -> SessionData | None:
        """Load session from file."""
        if not filepath.exists():
            return None

        try:
            with open(filepath) as f:
                data = json.load(f)

            return SessionData(
                metadata=SessionMetadata(**data.get("metadata", {})),
                messages=data.get("messages", []),
                stats=data.get("stats", {}),
                config=data.get("config", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def load_latest(self) -> SessionData | None:
        """Load most recent session."""
        sessions = self.list_sessions()
        if not sessions:
            return None

        latest = sessions[0]
        return self.load(latest["path"])

    def load_by_id(self, session_id: str) -> SessionData | None:
        """Load session by ID."""
        sessions = self.list_sessions()
        for s in sessions:
            if s["session_id"] == session_id:
                return self.load(s["path"])
        return None

    def list_sessions(self) -> List[dict]:
        """List all saved sessions."""
        sessions = []

        for filepath in self.storage_dir.glob("session_*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                sessions.append({
                    "path": filepath,
                    "session_id": metadata.get("session_id", ""),
                    "cwd": metadata.get("cwd", ""),
                    "created_at": metadata.get("created_at", 0),
                    "updated_at": metadata.get("updated_at", 0),
                    "message_count": metadata.get("message_count", 0),
                    "token_count": metadata.get("token_count", 0),
                    "model": metadata.get("model", ""),
                    "title": metadata.get("title", ""),
                })
            except (json.JSONDecodeError, IOError):
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s["updated_at"], reverse=True)

        return sessions

    def delete(self, filepath: Path) -> bool:
        """Delete session file."""
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def delete_by_id(self, session_id: str) -> bool:
        """Delete session by ID."""
        sessions = self.list_sessions()
        for s in sessions:
            if s["session_id"] == session_id:
                return self.delete(s["path"])
        return False

    def _generate_title(self, session: Session) -> str:
        """Generate session title from first message."""
        if not session.messages:
            return ""

        first_msg = session.messages[0]
        for block in first_msg.content:
            if hasattr(block, "text"):
                text = block.text[:50]
                return text + "..." if len(block.text) > 50 else text

        return ""

    def _cleanup_old_sessions(self) -> int:
        """Remove old sessions beyond limit."""
        sessions = self.list_sessions()

        if len(sessions) <= self.max_sessions:
            return 0

        to_remove = sessions[self.max_sessions:]
        removed = 0

        for s in to_remove:
            if self.delete(s["path"]):
                removed += 1

        return removed


class SessionRecovery:
    """Handles session recovery after crashes."""

    def __init__(self, persistence: Optional[SessionPersistence] = None):
        self.persistence = persistence or SessionPersistence()
        self.recovery_file = self.persistence.storage_dir / ".recovery"
        self._current_session_path: Optional[Path] = None
        self._auto_save_enabled = True
        self._auto_save_interval = 60.0  # seconds
        self._auto_save_task: asyncio.Task | None = None

    def start_auto_save(self, session: Session, engine: Any, config: Any) -> None:
        """Start auto-save task."""
        if self._auto_save_task:
            self._auto_save_task.cancel()

        self._auto_save_task = asyncio.create_task(
            self._auto_save_loop(session, engine, config),
        )

    def stop_auto_save(self) -> None:
        """Stop auto-save task."""
        if self._auto_save_task:
            self._auto_save_task.cancel()
            self._auto_save_task = None

    async def _auto_save_loop(self, session: Session, engine: Any, config: Any) -> None:
        """Auto-save loop."""
        while True:
            try:
                # Save session immediately on first iteration
                stats = engine.get_context_summary() if engine else {}
                config_dict = {
                    "model": config.api.model if config else "",
                }

                # Run save in executor to avoid blocking
                loop = asyncio.get_running_loop()
                path = await loop.run_in_executor(
                    None,
                    self.persistence.save,
                    session,
                    stats,
                    config_dict,
                )
                self._current_session_path = path

                # Write recovery file
                await loop.run_in_executor(
                    None,
                    self._write_recovery_file,
                    path,
                )

                # Then wait for next interval
                await asyncio.sleep(self._auto_save_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self._auto_save_interval)
                continue
                continue

    def _write_recovery_file(self, session_path: Path) -> None:
        """Write recovery marker."""
        with open(self.recovery_file, "w") as f:
            json.dump({
                "session_path": str(session_path),
                "timestamp": time.time(),
            }, f)

    def check_recovery(self) -> SessionData | None:
        """Check for recovery session."""
        if not self.recovery_file.exists():
            return None

        try:
            with open(self.recovery_file) as f:
                data = json.load(f)

            session_path = Path(data.get("session_path", ""))
            if session_path.exists():
                return self.persistence.load(session_path)

        except (json.JSONDecodeError, IOError):
            pass

        return None

    def clear_recovery(self) -> None:
        """Clear recovery marker."""
        if self.recovery_file.exists():
            self.recovery_file.unlink()

    def restore_session(self, session_data: SessionData) -> Session:
        """Restore session from data."""
        session = Session(
            cwd=Path(session_data.metadata.cwd),
            session_id=session_data.metadata.session_id,
        )

        # Restore created_at - convert timestamp back to datetime
        from datetime import datetime
        session.created_at = datetime.fromtimestamp(session_data.metadata.created_at)

        # Messages are restored via engine history
        return session


class SessionHistory:
    """Browse and manage session history."""

    def __init__(self, persistence: Optional[SessionPersistence] = None):
        self.persistence = persistence or SessionPersistence()

    def get_recent(self, limit: int = 10) -> List[dict]:
        """Get recent sessions."""
        sessions = self.persistence.list_sessions()
        return sessions[:limit]

    def search(self, query: str) -> List[dict]:
        """Search sessions by title/content."""
        sessions = self.persistence.list_sessions()
        results = []

        for s in sessions:
            if query.lower() in s.get("title", "").lower():
                results.append(s)
            elif query.lower() in s.get("cwd", "").lower():
                results.append(s)

        return results

    def get_session_summary(self, session_id: str) -> dict | None:
        """Get summary of specific session."""
        data = self.persistence.load_by_id(session_id)
        if data is None:
            return None

        return {
            "session_id": session_id,
            "cwd": data.metadata.cwd,
            "message_count": data.metadata.message_count,
            "token_count": data.metadata.token_count,
            "model": data.metadata.model,
            "created": time.strftime(
                "%Y-%m-%d %H:%M",
                time.localtime(data.metadata.created_at),
            ),
            "last_updated": time.strftime(
                "%Y-%m-%d %H:%M",
                time.localtime(data.metadata.updated_at),
            ),
        }

    def export_session(self, session_id: str, export_path: Path) -> bool:
        """Export session to file."""
        data = self.persistence.load_by_id(session_id)
        if data is None:
            return False

        with open(export_path, "w") as f:
            json.dump(asdict(data), f, indent=2)

        return True


# Global persistence instance
_persistence: Optional[SessionPersistence] = None


def get_persistence() -> SessionPersistence:
    """Get global persistence."""
    global _persistence
    if _persistence is None:
        _persistence = SessionPersistence()
    return _persistence


async def save_current_session(
    session: Session,
    engine: Any,
    config: Any,
) -> Path:
    """Save current session."""
    persistence = get_persistence()

    stats = engine.get_context_summary() if engine else {}
    config_dict = {"model": config.api.model if config else ""}

    return persistence.save(session, stats, config_dict)


def list_saved_sessions() -> List[dict]:
    """List all saved sessions."""
    return get_persistence().list_sessions()


def load_session(session_id: str) -> SessionData | None:
    """Load session by ID."""
    return get_persistence().load_by_id(session_id)
