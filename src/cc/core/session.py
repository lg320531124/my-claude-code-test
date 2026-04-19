"""Session management."""

from __future__ import annotations
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, ClassVar

from ..types.message import Message
from ..types.tool import ToolUseContext


class Session:
    """Manages a Claude Code session."""

    def __init__(
        self,
        cwd: Optional[Path] = None,
        session_id: Optional[str] = None,
    ):
        self.cwd = cwd or Path.cwd()
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: List[Message] = []
        self.started_at = datetime.now()

    def get_context(self) -> ToolUseContext:
        """Get tool execution context."""
        return ToolUseContext(
            cwd=str(self.cwd),
            session_id=self.session_id,
        )

    def add_message(self, message: Message) -> None:
        """Add message to session history."""
        self.messages.append(message)

    def clear_messages(self) -> None:
        """Clear session messages."""
        self.messages = []

    def save_transcript(self, path: Path) -> None:
        """Save session transcript to file."""
        import json
        data = {
            "session_id": self.session_id,
            "cwd": str(self.cwd),
            "started_at": self.started_at.isoformat(),
            "messages": [msg.model_dump() for msg in self.messages],
        }
        path.write_text(json.dumps(data, indent=2))

    def load_transcript(self, path: Path) -> None:
        """Load session transcript from file."""
        import json
        from ..types.message import Message
        data = json.loads(path.read_text())
        self.session_id = data["session_id"]
        self.cwd = Path(data["cwd"])
        self.messages = [Message.model_validate(m) for m in data["messages"]]


class SessionManager:
    """Manages multiple sessions and session history."""

    SESSIONS_DIR: ClassVar[Path] = Path.home() / ".claude" / "sessions"

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or self.SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[Session] = None

    def create_session(self, cwd: Optional[Path] = None) -> Session:
        """Create a new session."""
        session = Session(cwd=cwd)
        self._current_session = session
        self._save_session(session)
        return session

    def load_session(self, session_id: str) -> Session | None:
        """Load a session by ID."""
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            session = Session()
            session.load_transcript(path)
            self._current_session = session
            return session
        return None

    def save_session(self, session: Session) -> None:
        """Save a session."""
        self._save_session(session)

    def _save_session(self, session: Session) -> None:
        """Internal save method."""
        path = self.sessions_dir / f"{session.session_id}.json"
        session.save_transcript(path)

    def list_sessions(self) -> List[dict]:
        """List all saved sessions."""
        sessions = []
        for path in self.sessions_dir.glob("*.json"):
            try:
                import json
                data = json.loads(path.read_text())
                sessions.append({
                    "id": data.get("session_id", path.stem),
                    "created_at": data.get("started_at", ""),
                    "cwd": data.get("cwd", ""),
                    "message_count": len(data.get("messages", [])),
                    "last_active": path.stat().st_mtime,
                })
            except Exception:
                pass
        return sorted(sessions, key=lambda s: s["last_active"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def export_session(self, session_id: str, export_path: Path) -> bool:
        """Export a session to a specific path."""
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            export_path.write_text(path.read_text())
            return True
        return False

    def get_current_session(self) -> Session | None:
        """Get the current active session."""
        return self._current_session

    def clear_all(self) -> int:
        """Clear all sessions."""
        count = 0
        for path in self.sessions_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count
