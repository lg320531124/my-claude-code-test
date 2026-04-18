"""Theme command - UI theme management."""

from rich.console import Console
from rich.prompt import Prompt

from ..utils.config import Config


def run_theme(console: Console, theme: str | None = None) -> None:
    """Manage theme."""
    config = Config.load()

    if theme:
        # Set theme
        config.ui.theme = theme
        config.save()
        console.print(f"[green]Theme set to: {theme}[/green]")
    else:
        # Show current and options
        console.print(f"[bold]Current theme:[/bold] {config.ui.theme}")

        console.print("\n[bold]Available themes:[/bold]")
        themes = [
            ("dark", "Dark mode (default)"),
            ("light", "Light mode"),
            ("monochrome", "No colors"),
        ]

        for name, desc in themes:
            console.print(f"  [cyan]{name}[/] - {desc}")

        new_theme = Prompt.ask("Select theme", choices=["dark", "light", "monochrome"], default=config.ui.theme)

        if new_theme != config.ui.theme:
            config.ui.theme = new_theme
            config.save()
            console.print(f"[green]Theme changed to: {new_theme}[/green]")


def get_theme_colors(theme: str) -> dict:
    """Get color palette for theme."""
    if theme == "dark":
        return {
            "primary": "cyan",
            "secondary": "magenta",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "text": "white",
            "dim": "dim",
        }
    elif theme == "light":
        return {
            "primary": "blue",
            "secondary": "purple",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "text": "black",
            "dim": "grey50",
        }
    else:  # monochrome
        return {
            "primary": "bold",
            "secondary": "italic",
            "success": "",
            "warning": "",
            "error": "bold",
            "text": "",
            "dim": "dim",
        }