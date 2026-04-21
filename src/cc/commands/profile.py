"""Profile Command - Profile management."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table



def run_profile(console: Console, action: str = "list", name: Optional[str] = None) -> None:
    """Run profile command."""
    profiles_dir = Path.home() / ".claude" / "profiles"

    if action == "list":
        list_profiles(console, profiles_dir)
    elif action == "create":
        create_profile(console, profiles_dir, name)
    elif action == "switch":
        switch_profile(console, profiles_dir, name)
    elif action == "delete":
        delete_profile(console, profiles_dir, name)
    elif action == "show":
        show_profile(console, profiles_dir, name)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


def list_profiles(console: Console, profiles_dir: Path) -> None:
    """List all profiles."""
    profiles_dir.mkdir(parents=True, exist_ok=True)

    profiles = []
    for file in profiles_dir.glob("*.json"):
        profiles.append(file.stem)

    if not profiles:
        console.print("[dim]No profiles found[/dim]")
        console.print("[dim]Create one with: /profile create <name>[/dim]")
        return

    table = Table(title="Profiles")
    table.add_column("Name", style="cyan")
    table.add_column("Status")

    # Check current profile
    current = get_current_profile()

    for name in profiles:
        status = "[green]Active[/]" if name == current else ""
        table.add_row(name, status)

    console.print(table)


def create_profile(console: Console, profiles_dir: Path, name: Optional[str]) -> None:
    """Create a new profile."""
    if not name:
        console.print("[red]Profile name required[/red]")
        return

    profile_path = profiles_dir / f"{name}.json"
    if profile_path.exists():
        console.print(f"[red]Profile '{name}' already exists[/red]")
        return

    # Create default profile config
    import json
    config = {
        "api": {
            "model": "claude-opus-4-7",
            "base_url": None,
        },
        "ui": {
            "theme": "dark",
            "vim_mode": False,
        },
        "permissions": {
            "allow": [],
            "deny": [],
            "ask": [],
        },
    }

    profile_path.write_text(json.dumps(config, indent=2))
    console.print(f"[green]Profile '{name}' created[/green]")


def switch_profile(console: Console, profiles_dir: Path, name: Optional[str]) -> None:
    """Switch to a profile."""
    if not name:
        console.print("[red]Profile name required[/red]")
        return

    profile_path = profiles_dir / f"{name}.json"
    if not profile_path.exists():
        console.print(f"[red]Profile '{name}' not found[/red]")
        return

    # Set current profile marker
    marker_path = profiles_dir / ".current"
    marker_path.write_text(name)

    console.print(f"[green]Switched to profile '{name}'[/green]")


def delete_profile(console: Console, profiles_dir: Path, name: Optional[str]) -> None:
    """Delete a profile."""
    if not name:
        console.print("[red]Profile name required[/red]")
        return

    profile_path = profiles_dir / f"{name}.json"
    if not profile_path.exists():
        console.print(f"[red]Profile '{name}' not found[/red]")
        return

    profile_path.unlink()
    console.print(f"[green]Profile '{name}' deleted[/green]")


def show_profile(console: Console, profiles_dir: Path, name: Optional[str]) -> None:
    """Show profile details."""
    name = name or get_current_profile()
    if not name:
        console.print("[dim]No active profile[/dim]")
        return

    profile_path = profiles_dir / f"{name}.json"
    if not profile_path.exists():
        console.print(f"[red]Profile '{name}' not found[/red]")
        return

    import json
    config = json.loads(profile_path.read_text())

    console.print(f"[bold]Profile: {name}[/bold]\n")

    table = Table(show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    # API settings
    table.add_row("Model", config.get("api", {}).get("model", "default"))
    table.add_row("Theme", config.get("ui", {}).get("theme", "dark"))

    console.print(table)


def get_current_profile() -> Optional[str]:
    """Get current profile name."""
    profiles_dir = Path.home() / ".claude" / "profiles"
    marker_path = profiles_dir / ".current"

    if marker_path.exists():
        return marker_path.read_text().strip()
    return None


__all__ = ["run_profile", "get_current_profile"]