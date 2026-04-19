"""Diff command - View changes."""

from __future__ import annotations
import subprocess
from pathlib import Path

from rich.console import Console


def run_diff(console: Console, cwd: Path, file: Optional[str] = None, staged: bool = True) -> None:
    """View git diff."""
    try:
        if file:
            # Diff specific file
            cmd = ["git", "diff", "--cached" if staged else "", file]
        else:
            # Diff all
            cmd = ["git", "diff", "--cached" if staged else "", "--stat"]

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            if staged:
                console.print("[yellow]No staged changes[/yellow]")
                # Show unstaged
                unstaged = subprocess.run(
                    ["git", "diff", "--stat"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                )
                if unstaged.stdout.strip():
                    console.print("[dim]Unstaged changes exist[/dim]")
            else:
                console.print("[yellow]No changes[/yellow]")
            return

        # Show diff
        console.print("[bold]Changes:[/bold]")
        console.print(result.stdout)

        if not file and staged:
            # Show full diff for staged
            full_diff = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            if full_diff.stdout.strip():
                console.print("\n[bold]Diff content:[/bold]")
                _print_diff(console, full_diff.stdout)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error: {e.stderr}[/red]")


def _print_diff(console: Console, diff: str) -> None:
    """Print diff with colors."""
    for line in diff.split("\n"):
        if line.startswith("+"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@"):
            console.print(f"[cyan]{line}[/cyan]")
        elif line.startswith("diff --git"):
            console.print(f"[bold]{line}[/bold]")
        else:
            console.print(line)
