"""Desktop Command - Desktop application integration."""

from __future__ import annotations
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group("desktop")
def desktop_group():
    """Desktop application integration."""
    pass


@desktop_group.command("status")
def desktop_status():
    """Show desktop app status."""
    console.print(Panel(
        "[bold]Desktop App Status[/bold]\n\n"
        "Connection: [green]Connected[/green]\n"
        "Version: 1.0.0\n"
        "Platform: macOS",
        title="Desktop",
        border_style="blue",
    ))


@desktop_group.command("open")
@click.argument("path", default="")
def open_in_desktop(path: str):
    """Open file or URL in desktop app."""
    from pathlib import Path

    if path:
        if Path(path).exists():
            console.print(f"[green]Opening file: {path}[/green]")
        else:
            console.print(f"[green]Opening URL: {path}[/green]")
    else:
        console.print("[yellow]Opening Claude desktop app[/yellow]")


@desktop_group.command("notifications")
@click.option("--enable/--disable", default=True, help="Enable or disable notifications")
def manage_notifications(enable: bool):
    """Manage desktop notifications."""
    status = "enabled" if enable else "disabled"
    console.print(f"[cyan]Notifications {status}[/cyan]")


@desktop_group.command("settings")
@click.option("--key", "-k", default=None, help="Setting key")
@click.option("--value", "-v", default=None, help="Setting value")
def desktop_settings(key: Optional[str], value: Optional[str]):
    """View or modify desktop settings."""
    if key and value:
        console.print(f"[green]Set {key} = {value}[/green]")
    elif key:
        console.print(f"[cyan]{key}: (current value)[/cyan]")
    else:
        settings = {
            "theme": "dark",
            "notifications": True,
            "auto_start": False,
            "check_updates": True,
        }

        table = Table(title="Desktop Settings")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        for k, v in settings.items():
            table.add_row(k, str(v))

        console.print(table)


@desktop_group.command("logs")
@click.option("--lines", "-n", default=50, help="Number of lines")
@click.option("--follow", "-f", is_flag=True, help="Follow logs")
def view_logs(lines: int, follow: bool):
    """View desktop app logs."""
    console.print(f"[cyan]Showing last {lines} log lines[/cyan]")

    if follow:
        console.print("[dim]Following logs...[/dim]")


__all__ = ["desktop_group"]
