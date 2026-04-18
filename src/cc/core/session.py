"""Session management."""

import uuid
from datetime import datetime
from pathlib import Path

from ..types.message import Message
from ..types.tool import ToolUseContext


class Session:
    """Manages a Claude Code session."""

    def __init__(
        self,
        cwd: Path | None = None,
        session_id: str | None = None,
    ):
        self.cwd = cwd or Path.cwd()
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: list[Message] = []
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