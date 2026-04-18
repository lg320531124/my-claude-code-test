"""Usage command - Detailed usage stats."""

import json
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table


USAGE_FILE = Path.home() / ".claude-code-py" / "usage.json"


def run_usage(console: Console, period: str = "session") -> None:
    """Show detailed usage."""
    if period == "session":
        show_session_usage(console)
    elif period == "daily":
        show_daily_usage(console)
    elif period == "all":
        show_all_usage(console)
    else:
        console.print(f"[red]Unknown period: {period}[/red]")


def show_session_usage(console: Console) -> None:
    """Show current session usage."""
    from .cost import get_tracker

    tracker = get_tracker()
    summary = tracker.get_summary()

    table = Table(title="Session Usage")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    for key, value in summary.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    table.add_row("Estimated Cost", f"${tracker.estimate_cost():.4f}")

    console.print(table)


def show_daily_usage(console: Console) -> None:
    """Show daily usage."""
    if not USAGE_FILE.exists():
        console.print("[yellow]No usage history[/yellow]")
        return

    try:
        data = json.loads(USAGE_FILE.read_text())
        today = datetime.now().strftime("%Y-%m-%d")

        if today not in data:
            console.print("[yellow]No usage recorded today[/yellow]")
            return

        day_data = data[today]

        table = Table(title=f"Usage for {today}")
        table.add_column("Session", style="cyan")
        table.add_column("Tokens")
        table.add_column("Cost")

        total_tokens = 0
        total_cost = 0

        for session_id, usage in day_data.items():
            tokens = usage.get("total_tokens", 0)
            cost = usage.get("cost", 0)
            total_tokens += tokens
            total_cost += cost
            table.add_row(session_id[:8], str(tokens), f"${cost:.4f}")

        table.add_row("[bold]Total[/]", str(total_tokens), f"${total_cost:.4f}")

        console.print(table)

    except json.JSONDecodeError:
        console.print("[red]Invalid usage file[/red]")


def show_all_usage(console: Console) -> None:
    """Show all usage history."""
    if not USAGE_FILE.exists():
        console.print("[yellow]No usage history[/yellow]")
        return

    try:
        data = json.loads(USAGE_FILE.read_text())

        table = Table(title="Usage History")
        table.add_column("Date", style="cyan")
        table.add_column("Sessions")
        table.add_column("Total Tokens")
        table.add_column("Total Cost")

        for date, day_data in sorted(data.items(), reverse=True):
            sessions = len(day_data)
            tokens = sum(u.get("total_tokens", 0) for u in day_data.values())
            cost = sum(u.get("cost", 0) for u in day_data.values())
            table.add_row(date, str(sessions), str(tokens), f"${cost:.4f}")

        console.print(table)

    except json.JSONDecodeError:
        console.print("[red]Invalid usage file[/red]")


def save_usage(session_id: str, usage: dict) -> None:
    """Save usage to file."""
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if USAGE_FILE.exists():
        try:
            data = json.loads(USAGE_FILE.read_text())
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    today = datetime.now().strftime("%Y-%m-%d")
    if today not in data:
        data[today] = {}

    data[today][session_id] = usage

    USAGE_FILE.write_text(json.dumps(data, indent=2))