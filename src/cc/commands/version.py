"""Version Command - Version info."""

from __future__ import annotations
from rich.console import Console
from rich.table import Table

from cc import __version__


def run_version(console: Console, detail: bool = False) -> None:
    """Run version command."""
    console.print(f"[bold]Claude Code Python[/bold] v{__version__}\n")

    if detail:
        show_version_details(console)


def show_version_details(console: Console) -> None:
    """Show detailed version info."""
    import sys
    import platform

    table = Table(title="Version Details")
    table.add_column("Component", style="cyan")
    table.add_column("Version")

    # Python version
    table.add_row("Python", sys.version.split()[0])

    # Platform
    table.add_row("Platform", platform.platform())

    # Claude Code version
    table.add_row("Claude Code", __version__)

    # Check dependencies
    deps = [
        ("pydantic", "pydantic"),
        ("rich", "rich"),
        ("click", "click"),
        ("httpx", "httpx"),
        ("textual", "textual"),
    ]

    for name, module in deps:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            table.add_row(name, version)
        except ImportError:
            table.add_row(name, "[dim]not installed[/dim]")

    console.print(table)

    # Show paths
    console.print("\n[bold]Paths[/bold]")
    import cc
    console.print(f"[dim]Package: {cc.__file__}[/dim]")

    from pathlib import Path
    config_path = Path.home() / ".claude" / "settings.json"
    console.print(f"[dim]Config: {config_path}[/dim]")


__all__ = ["run_version"]