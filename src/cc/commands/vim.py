"""Vim command - Vim mode toggle."""

from rich.console import Console
from rich.prompt import Prompt

from ..utils.config import Config


def run_vim(console: Console, enable: bool | None = None) -> None:
    """Toggle vim mode."""
    config = Config.load()

    # Check if vim mode setting exists
    vim_enabled = getattr(config.ui, "vim_mode", False)

    if enable is not None:
        vim_enabled = enable
    else:
        # Toggle
        console.print(f"[bold]Vim mode:[/bold] {vim_enabled}")
        choice = Prompt.ask("Enable vim mode?", choices=["y", "n"], default="y" if not vim_enabled else "n")
        vim_enabled = choice == "y"

    # Save setting
    config.ui.vim_mode = vim_enabled
    config.save()

    status = "enabled" if vim_enabled else "disabled"
    console.print(f"[green]Vim mode {status}[/green]")

    if vim_enabled:
        console.print("\n[dim]Vim keybindings:[/dim]")
        console.print("[dim]  i - Enter insert mode[/dim]")
        console.print("[dim]  Esc - Exit insert mode[/dim]")
        console.print("[dim]  : - Command mode[/dim]")
        console.print("[dim]  w - Save[/dim]")
        console.print("[dim]  q - Quit[/dim]")


def get_vim_keybindings() -> dict:
    """Get vim keybinding mappings."""
    return {
        "i": "enter_insert",
        "a": "append",
        "o": "open_below",
        "O": "open_above",
        "Esc": "exit_insert",
        ":": "command_mode",
        "w": "save",
        "q": "quit",
        "d": "delete_line",
        "y": "yank",
        "p": "paste",
        "u": "undo",
        "/": "search",
        "n": "next_search",
        "N": "prev_search",
        "h": "move_left",
        "j": "move_down",
        "k": "move_up",
        "l": "move_right",
        "0": "line_start",
        "$": "line_end",
        "gg": "file_start",
        "G": "file_end",
    }