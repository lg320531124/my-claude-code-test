"""Sessions command - Manage saved sessions."""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import ClassVar

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel


async def list_sessions_async(console: Console) -> None:
    """List all saved sessions."""
    from ..core.recovery import list_saved_sessions, SessionHistory

    sessions = list_saved_sessions()

    if not sessions:
        console.print("[dim]No saved sessions[/dim]")
        return

    table = Table(title="Saved Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("CWD")
    table.add_column("Messages")
    table.add_column("Last Updated")
    table.add_column("Model")

    for s in sessions[:20]:  # Limit display
        session_id = s["session_id"][:16] if s["session_id"] else "unknown"
        cwd = str(Path(s["cwd"]).name) if s["cwd"] else "unknown"
        msgs = s["message_count"]
        updated = time.strftime(
            "%Y-%m-%d %H:%M",
            time.localtime(s["updated_at"]),
        )
        model = s["model"] or "unknown"

        table.add_row(session_id, cwd, str(msgs), updated, model)

    console.print(table)
    console.print(f"\n[dim]Total: {len(sessions)} sessions[/dim]")


async def load_session_async(console: Console, session_id: str) -> None:
    """Load a saved session."""
    from ..core.recovery import load_session, SessionRecovery

    data = load_session(session_id)

    if data is None:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    console.print(Panel(
        f"Session ID: {data.metadata.session_id}\n"
        f"CWD: {data.metadata.cwd}\n"
        f"Messages: {data.metadata.message_count}\n"
        f"Model: {data.metadata.model}",
        title="Session Loaded",
        border_style="green",
    ))

    # Show first few messages
    console.print("\n[bold]Recent Messages:[/bold]")
    for i, msg in enumerate(data.messages[:5]):
        role = msg.get("role", "unknown")
        content_preview = ""
        for block in msg.get("content", []):
            if block.get("type") == "text":
                text = block.get("text", "")
                content_preview = text[:50] + "..." if len(text) > 50 else text
                break

        console.print(f"  {i+1}. [{role}] {content_preview}")


async def delete_session_async(console: Console, session_id: str) -> bool:
    """Delete a saved session."""
    from ..core.recovery import get_persistence

    persistence = get_persistence()

    # Confirm
    if not Confirm.ask(f"Delete session {session_id}?"):
        return False

    result = persistence.delete_by_id(session_id)

    if result:
        console.print(f"[green]Deleted: {session_id}[/green]")
    else:
        console.print(f"[red]Session not found: {session_id}[/red]")

    return result


async def export_session_async(console: Console, session_id: str, output_path: Path) -> bool:
    """Export session to file."""
    from ..core.recovery import SessionHistory, get_persistence

    history = SessionHistory(get_persistence())

    result = history.export_session(session_id, output_path)

    if result:
        console.print(f"[green]Exported to: {output_path}[/green]")
    else:
        console.print(f"[red]Failed to export[/red]")

    return result


async def clear_old_sessions_async(console: Console, days: int = 30) -> int:
    """Clear old sessions."""
    from ..core.recovery import get_persistence

    persistence = get_persistence()
    sessions = persistence.list_sessions()

    cutoff = time.time() - (days * 86400)
    to_delete = [s for s in sessions if s["updated_at"] < cutoff]

    if not to_delete:
        console.print("[dim]No old sessions to clear[/dim]")
        return 0

    console.print(f"[yellow]Found {len(to_delete)} sessions older than {days} days[/yellow]")

    if not Confirm.ask("Delete these sessions?"):
        return 0

    deleted = 0
    for s in to_delete:
        if persistence.delete_by_id(s["session_id"]):
            deleted += 1

    console.print(f"[green]Deleted {deleted} old sessions[/green]")
    return deleted


def run_sessions(console: Console, action: str = "list", args: List[str] = []) -> None:
    """Run sessions command."""
    cwd = Path.cwd()

    if action == "list":
        asyncio.run(list_sessions_async(console))
    elif action == "load":
        session_id = args[0] if args else Prompt.ask("Session ID")
        asyncio.run(load_session_async(console, session_id))
    elif action == "delete":
        session_id = args[0] if args else Prompt.ask("Session ID")
        asyncio.run(delete_session_async(console, session_id))
    elif action == "export":
        session_id = args[0] if args else Prompt.ask("Session ID")
        output = args[1] if len(args) > 1 else Prompt.ask("Output file", default=f"{session_id}.json")
        asyncio.run(export_session_async(console, session_id, Path(output)))
    elif action == "clear":
        days = int(args[0]) if args else 30
        asyncio.run(clear_old_sessions_async(console, days))
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Actions: list, load, delete, export, clear")
