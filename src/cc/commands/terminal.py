"""Terminal Command - Terminal management."""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group("terminal")
def terminal_group():
    """Terminal management."""
    pass


@terminal_group.command("info")
def terminal_info():
    """Show terminal information."""
    import os

    term_type = os.environ.get("TERM", "unknown")
    shell = os.environ.get("SHELL", "unknown")
    editor = os.environ.get("EDITOR", "unknown")

    console.print(Panel(
        f"[bold]Terminal Info[/bold]\n\n"
        f"Type: {term_type}\n"
        f"Shell: {shell}\n"
        f"Editor: {editor}\n"
        f"Colors: {console.color_system}",
        title="Terminal",
        border_style="blue",
    ))


@terminal_group.command("size")
def terminal_size():
    """Show terminal size."""
    import os

    try:
        size = os.get_terminal_size()
        console.print(f"[cyan]Columns: {size.columns}[/cyan]")
        console.print(f"[cyan]Lines: {size.lines}[/cyan]")
    except OSError:
        console.print("[yellow]Terminal size unavailable[/yellow]")


@terminal_group.command("clear")
def clear_terminal():
    """Clear terminal screen."""
    console.clear()
    console.print("[green]Screen cleared[/green]")


@terminal_group.command("title")
@click.argument("title")
def set_title(title: str):
    """Set terminal window title."""
    console.print(f"\033]0;{title}\007", end="")
    console.print(f"[dim]Title set to: {title}[/dim]")


@terminal_group.command("bell")
def ring_bell():
    """Ring terminal bell."""
    console.print("\a", end="")
    console.print("[dim]Bell rang[/dim]")


@terminal_group.command("env")
@click.argument("name", default=None, required=False)
def show_env(name: Optional[str] = None):
    """Show environment variables."""
    import os

    if name:
        value = os.environ.get(name)
        if value:
            console.print(f"[cyan]{name}[/cyan] = [white]{value}[/white]")
        else:
            console.print(f"[yellow]{name} not set[/yellow]")
    else:
        table = Table(title="Environment Variables")
        table.add_column("Name", style="cyan")
        table.add_column("Value", style="white")

        # Show relevant env vars
        relevant = ["PATH", "HOME", "USER", "TERM", "SHELL", "EDITOR"]
        for key in relevant:
            value = os.environ.get(key, "")
            table.add_row(key, value[:50] + "..." if len(value) > 50 else value)

        console.print(table)


__all__ = ["terminal_group"]
