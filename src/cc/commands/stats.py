"""Statistics Command - Usage statistics."""

from __future__ import annotations
from pathlib import Path
import json
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..services.analytics.analytics import get_analytics_service


def run_stats(console: Console, period: str = "session", detail: Optional[str] = None) -> None:
    """Run statistics command."""
    console.print("[bold]Usage Statistics[/bold]\n")

    if period == "session":
        show_session_stats(console)
    elif period == "daily":
        show_daily_stats(console)
    elif period == "weekly":
        show_weekly_stats(console)
    elif period == "all":
        show_all_stats(console)
    else:
        console.print(f"[red]Unknown period: {period}[/red]")

    if detail:
        show_detail(console, detail)


def show_session_stats(console: Console) -> None:
    """Show current session statistics."""
    analytics = get_analytics_service()

    # Get session stats
    events = analytics.get_events()

    table = Table(title="Session Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    # Count events
    api_calls = len([e for e in events if e.event_type == "api_call"])
    tool_calls = len([e for e in events if e.event_type == "tool_use"])
    errors = len([e for e in events if e.event_type == "error"])

    # Token totals
    total_input = sum(
        e.data.get("input_tokens", 0)
        for e in events
        if e.event_type == "api_call"
    )
    total_output = sum(
        e.data.get("output_tokens", 0)
        for e in events
        if e.event_type == "api_call"
    )

    table.add_row("API Calls", str(api_calls))
    table.add_row("Tool Calls", str(tool_calls))
    table.add_row("Input Tokens", str(total_input))
    table.add_row("Output Tokens", str(total_output))
    table.add_row("Total Tokens", str(total_input + total_output))
    table.add_row("Errors", str(errors))

    console.print(table)


def show_daily_stats(console: Console) -> None:
    """Show daily statistics."""
    storage_path = Path.home() / ".claude" / "analytics"
    today_file = storage_path / f"events_{get_today_date()}.jsonl"

    if not today_file.exists():
        console.print("[dim]No data for today[/dim]")
        return

    events = []
    for line in today_file.read_text().splitlines():
        if line.strip():
            events.append(json.loads(line))

    table = Table(title="Daily Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    api_calls = len([e for e in events if e.get("event_type") == "api_call"])
    tool_calls = len([e for e in events if e.get("event_type") == "tool_use"])

    table.add_row("API Calls", str(api_calls))
    table.add_row("Tool Calls", str(tool_calls))
    table.add_row("Sessions", str(count_sessions(events)))
    table.add_row("Commands", str(len([e for e in events if e.get("event_type") == "command"])))

    console.print(table)


def show_weekly_stats(console: Console) -> None:
    """Show weekly statistics."""
    console.print("[dim]Weekly stats require 7 days of data[/dim]")

    storage_path = Path.home() / ".claude" / "analytics"

    # Aggregate week
    total_api = 0
    total_tools = 0

    for i in range(7):
        date = get_date_days_ago(i)
        file = storage_path / f"events_{date}.jsonl"
        if file.exists():
            for line in file.read_text().splitlines():
                if line.strip():
                    event = json.loads(line)
                    if event.get("event_type") == "api_call":
                        total_api += 1
                    if event.get("event_type") == "tool_use":
                        total_tools += 1

    table = Table(title="Weekly Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("API Calls", str(total_api))
    table.add_row("Tool Calls", str(total_tools))
    table.add_row("Avg API/Day", str(total_api // 7))

    console.print(table)


def show_all_stats(console: Console) -> None:
    """Show all-time statistics."""
    storage_path = Path.home() / ".claude" / "analytics"

    if not storage_path.exists():
        console.print("[dim]No analytics data[/dim]")
        return

    total_events = 0
    total_api = 0
    total_tools = 0

    for file in storage_path.glob("events_*.jsonl"):
        for line in file.read_text().splitlines():
            if line.strip():
                event = json.loads(line)
                total_events += 1
                if event.get("event_type") == "api_call":
                    total_api += 1
                if event.get("event_type") == "tool_use":
                    total_tools += 1

    table = Table(title="All-Time Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Total Events", str(total_events))
    table.add_row("API Calls", str(total_api))
    table.add_row("Tool Calls", str(total_tools))
    table.add_row("Days Recorded", str(len(list(storage_path.glob("events_*.jsonl")))))

    console.print(table)


def show_detail(console: Console, detail_type: str) -> None:
    """Show detailed breakdown."""
    analytics = get_analytics_service()
    events = analytics.get_events()

    if detail_type == "tools":
        # Tool breakdown
        tool_counts = {}
        for e in events:
            if e.event_type == "tool_use":
                tool = e.data.get("tool", "unknown")
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        table = Table(title="Tool Usage Breakdown")
        table.add_column("Tool", style="cyan")
        table.add_column("Count")

        for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            table.add_row(tool, str(count))

        console.print(table)

    elif detail_type == "errors":
        # Error breakdown
        error_types = {}
        for e in events:
            if e.event_type == "error":
                err_type = e.data.get("type", "unknown")
                error_types[err_type] = error_types.get(err_type, 0) + 1

        if error_types:
            table = Table(title="Error Breakdown")
            table.add_column("Type", style="cyan")
            table.add_column("Count")

            for err_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                table.add_row(err_type, str(count))

            console.print(table)
        else:
            console.print("[green]No errors[/green]")


def get_today_date() -> str:
    """Get today's date string."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def get_date_days_ago(days: int) -> str:
    """Get date string for days ago."""
    from datetime import datetime, timedelta
    date = datetime.now() - timedelta(days=days)
    return date.strftime("%Y-%m-%d")


def count_sessions(events: list) -> int:
    """Count unique sessions."""
    sessions = set()
    for e in events:
        if "session_id" in e.get("data", {}):
            sessions.add(e["data"]["session_id"])
    return len(sessions)


__all__ = ["run_stats"]