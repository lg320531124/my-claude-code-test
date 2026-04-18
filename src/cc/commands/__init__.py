"""Commands module."""

from rich.console import Console

from ..core.session import Session


async def handle_command(command: str, session: Session, console: Console) -> None:
    """Handle a slash command."""
    cmd = command.strip().lower()

    if cmd == "/help":
        show_help(console)
    elif cmd == "/doctor":
        from .doctor import run_doctor
        run_doctor(console)
    elif cmd == "/clear":
        session.clear_messages()
        console.print("[green]Session cleared[/green]")
    elif cmd == "/exit":
        console.print("[yellow]Goodbye![/yellow]")
        raise SystemExit(0)
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        show_help(console)


def show_help(console: Console) -> None:
    """Show help for commands."""
    from rich.table import Table

    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("/help", "Show this help"),
        ("/doctor", "Run diagnostics"),
        ("/clear", "Clear session"),
        ("/exit", "Exit REPL"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)