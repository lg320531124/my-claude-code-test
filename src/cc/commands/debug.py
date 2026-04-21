"""Debug Command - Debug mode."""

from __future__ import annotations
from pathlib import Path
from rich.console import Console



def run_debug(console: Console, action: str = "status") -> None:
    """Run debug command."""
    if action == "status":
        show_debug_status(console)
    elif action == "enable":
        enable_debug(console)
    elif action == "disable":
        disable_debug(console)
    elif action == "log":
        show_debug_log(console)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


def show_debug_status(console: Console) -> None:
    """Show debug status."""
    debug_enabled = is_debug_enabled()

    if debug_enabled:
        console.print("[green]Debug mode: ENABLED[/green]")
    else:
        console.print("[dim]Debug mode: DISABLED[/dim]")

    # Show debug file location
    log_path = Path.home() / ".claude" / "debug.log"
    console.print(f"[dim]Debug log: {log_path}[/dim]")


def enable_debug(console: Console) -> None:
    """Enable debug mode."""
    config_path = Path.home() / ".claude" / "settings.json"

    import json
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        config = {}

    config["debug"] = True
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))

    console.print("[green]Debug mode enabled[/green]")
    console.print("[dim]Logs will be written to ~/.claude/debug.log[/dim]")


def disable_debug(console: Console) -> None:
    """Disable debug mode."""
    config_path = Path.home() / ".claude" / "settings.json"

    import json
    if config_path.exists():
        config = json.loads(config_path.read_text())
        config["debug"] = False
        config_path.write_text(json.dumps(config, indent=2))

    console.print("[green]Debug mode disabled[/green]")


def show_debug_log(console: Console) -> None:
    """Show debug log contents."""
    log_path = Path.home() / ".claude" / "debug.log"

    if not log_path.exists():
        console.print("[dim]No debug log[/dim]")
        return

    content = log_path.read_text()

    # Show last 50 lines
    lines = content.splitlines()
    if len(lines) > 50:
        console.print(f"[dim]Showing last 50 of {len(lines)} lines[/dim]\n")
        lines = lines[-50:]

    for line in lines:
        console.print(line)


def is_debug_enabled() -> bool:
    """Check if debug is enabled."""
    config_path = Path.home() / ".claude" / "settings.json"

    if config_path.exists():
        import json
        config = json.loads(config_path.read_text())
        return config.get("debug", False)

    return False


__all__ = ["run_debug", "is_debug_enabled"]