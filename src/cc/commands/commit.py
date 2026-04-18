"""Commit command - Create git commits."""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt


def run_commit(console: Console, cwd: Path, message: str | None = None) -> None:
    """Create a git commit."""
    # Check git status
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    if not result.stdout.strip():
        console.print("[yellow]No changes to commit[/yellow]")
        return

    # Show changes
    console.print("[bold]Changes:[/bold]")
    for line in result.stdout.strip().split("\n"):
        status = line[:2].strip()
        file = line[3:]
        status_color = {"M": "yellow", "A": "green", "D": "red", "?": "blue"}
        color = status_color.get(status, "white")
        console.print(f"  [{color}]{status}[/{color}] {file}")

    # Generate commit message if not provided
    if not message:
        # Get diff summary
        diff_result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        console.print(f"\n[dim]{diff_result.stdout}[/dim]")

        message = Prompt.ask("[bold]Commit message[/bold]")

    if not message.strip():
        console.print("[red]Empty commit message[/red]")
        return

    # Stage changes
    subprocess.run(["git", "add", "-A"], cwd=cwd)

    # Create commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        console.print(f"[green]✓ Committed: {message}[/green]")
    else:
        console.print(f"[red]Commit failed: {result.stderr}[/red]")


def get_git_info(cwd: Path) -> dict:
    """Get git repository info."""
    info = {"in_repo": False}

    try:
        # Check if in repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return info

        info["in_repo"] = True

        # Get branch
        info["branch"] = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Get remote
        info["remote"] = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Get status
        info["status"] = subprocess.run(
            ["git", "status", "--short"],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Get last commit
        info["last_commit"] = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout.strip()

    except Exception:
        pass

    return info