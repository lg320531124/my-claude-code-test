"""Resume command - Resume previous session."""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ..core.session import Session


SESSIONS_DIR = Path.home() / ".claude-code-py" / "sessions"


def run_resume(console: Console, session_id: Optional[str] = None) -> Session | None:
    """Resume a previous session."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if session_id:
        return load_session(console, session_id)

    # List available sessions
    sessions = list_sessions()

    if not sessions:
        console.print("[yellow]No previous sessions found[/yellow]")
        return None

    # Show sessions
    table = Table(title="Recent Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Date")
    table.add_column("Messages")
    table.add_column("CWD")

    for s in sessions[:10]:  # Show last 10
        table.add_row(
            s["id"][:8],
            s["date"],
            str(s["message_count"]),
            s["cwd"][:30],
        )

    console.print(table)

    # Ask which to resume
    choice = Prompt.ask("Resume session (ID or 'new')", default="new")

    if choice == "new":
        return None

    return load_session(console, choice)


def load_session(console: Console, session_id: str) -> Session | None:
    """Load a session by ID."""
    # Find session file
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(session_file.read_text())
            if data.get("session_id", "").startswith(session_id):
                session = Session()
                session.load_transcript(session_file)
                console.print(f"[green]Resumed session: {session.session_id[:8]}[/green]")
                console.print(f"[dim]Messages: {len(session.messages)}[/dim]")
                console.print(f"[dim]CWD: {session.cwd}[/dim]")
                return session
        except json.JSONDecodeError:
            pass

    console.print(f"[red]Session not found: {session_id}[/red]")
    return None


def list_sessions() -> List[dict]:
    """List all saved sessions."""
    sessions = []

    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(session_file.read_text())
            sessions.append({
                "id": data.get("session_id", "unknown"),
                "date": data.get("started_at", "unknown"),
                "cwd": data.get("cwd", "unknown"),
                "message_count": len(data.get("messages", [])),
                "file": str(session_file),
            })
        except json.JSONDecodeError:
            pass

    # Sort by date
    sessions.sort(key=lambda x: x.get("date", ""), reverse=True)

    return sessions


def save_session(session: Session) -> Path:
    """Save session to file."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{session.session_id}.json"
    path = SESSIONS_DIR / filename

    session.save_transcript(path)

    return path


def cleanup_old_sessions(days: int = 7) -> int:
    """Clean up sessions older than N days."""
    import time

    count = 0
    cutoff = time.time() - (days * 24 * 60 * 60)

    for session_file in SESSIONS_DIR.glob("*.json"):
        if session_file.stat().st_mtime < cutoff:
            session_file.unlink()
            count += 1

    return count
