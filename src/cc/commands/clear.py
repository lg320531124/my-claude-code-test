"""Clear Command - Clear various data."""

from __future__ import annotations
from pathlib import Path
from rich.console import Console

from ..core.session import Session


def run_clear(console: Console, session: Session, target: str = "messages") -> None:
    """Run clear command."""
    if target == "messages":
        clear_messages(console, session)
    elif target == "history":
        clear_history(console, session)
    elif target == "cache":
        clear_cache(console)
    elif target == "analytics":
        clear_analytics(console)
    elif target == "all":
        clear_all(console, session)
    else:
        console.print(f"[red]Unknown target: {target}[/red]")
        console.print("[dim]Valid targets: messages, history, cache, analytics, all[/dim]")


def clear_messages(console: Console, session: Session) -> None:
    """Clear session messages."""
    count = len(session.messages)
    session.messages.clear()
    console.print(f"[green]Cleared {count} messages[/green]")


def clear_history(console: Console, session: Session) -> None:
    """Clear session history."""
    # Also clear any persistent history
    history_path = Path.home() / ".claude" / "history.json"
    if history_path.exists():
        history_path.unlink()

    session.messages.clear()
    console.print("[green]Cleared session history[/green]")


def clear_cache(console: Console) -> None:
    """Clear cache."""
    cache_path = Path.home() / ".claude" / "cache"
    if cache_path.exists():
        import shutil
        shutil.rmtree(cache_path)
        console.print("[green]Cleared cache[/green]")
    else:
        console.print("[dim]No cache to clear[/dim]")


def clear_analytics(console: Console) -> None:
    """Clear analytics data."""
    analytics_path = Path.home() / ".claude" / "analytics"
    if analytics_path.exists():
        files = list(analytics_path.glob("*.jsonl"))
        for f in files:
            f.unlink()
        console.print(f"[green]Cleared {len(files)} analytics files[/green]")
    else:
        console.print("[dim]No analytics to clear[/dim]")


def clear_all(console: Console, session: Session) -> None:
    """Clear all data."""
    clear_messages(console, session)
    clear_cache(console)
    clear_analytics(console)
    console.print("[green]All data cleared[/green]")


__all__ = ["run_clear"]