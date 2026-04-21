"""Session management."""

from __future__ import annotations
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, ClassVar, List, Dict, Any

from ..types.message import Message, UserMessage, TextBlock
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
        self.created_at = datetime.now()  # Alias for started_at
        self.metadata: Dict[str, Any] = {}
        self.git_branch: Optional[str] = None

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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dict."""
        messages_data = []
        for m in self.messages:
            content_list = []
            content = m.content if isinstance(m.content, list) else [m.content]
            for c in content:
                if hasattr(c, 'text'):
                    content_list.append({"type": "text", "text": c.text})
                else:
                    content_list.append({"type": "text", "text": str(c)})
            messages_data.append({"role": m.role, "content": content_list})

        return {
            "session_id": self.session_id,
            "cwd": str(self.cwd),
            "started_at": self.started_at.isoformat(),
            "messages": messages_data,
            "metadata": self.metadata,
            "git_branch": self.git_branch,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Session:
        """Deserialize session from dict."""
        session = cls(
            cwd=Path(data.get("cwd", "/tmp")),
            session_id=data.get("session_id"),
        )
        session.metadata = data.get("metadata", {})
        session.git_branch = data.get("git_branch")

        # Parse messages
        for msg_data in data.get("messages", []):
            if msg_data.get("role") == "user":
                content = msg_data.get("content", [])
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                if text_parts:
                    session.messages.append(UserMessage(content=[TextBlock(text=" ".join(text_parts))]))

        return session


class SessionManager:
    """Manages multiple sessions and session history."""

    SESSIONS_DIR: ClassVar[Path] = Path.home() / ".claude" / "sessions"

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or self.SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[Session] = None
        self.sessions: Dict[str, Session] = {}  # Active sessions dict

    def create_session(self, cwd: Optional[Path] = None) -> Session:
        """Create a new session."""
        session = Session(cwd=cwd)
        self._current_session = session
        self.sessions[session.session_id] = session  # Add to dict
        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def end_session(self, session_id: str) -> None:
        """End and remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

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
