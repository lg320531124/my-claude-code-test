"""Review command - Code review."""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table


def run_review(console: Console, cwd: Path) -> None:
    """Review current changes."""
    # Get git diff
    result = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    if not result.stdout.strip():
        console.print("[yellow]No staged changes to review[/yellow]")
        # Check unstaged
        unstaged = subprocess.run(
            ["git", "diff", "HEAD", "--stat"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if unstaged.stdout.strip():
            console.print("[dim]Unstaged changes exist. Use 'git add' to stage.[/dim]")
        return

    console.print("[bold]Files changed:[/bold]")
    console.print(result.stdout)

    # Get diff content
    diff_result = subprocess.run(
        ["git", "diff"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    # Analyze changes
    changes = analyze_diff(diff_result.stdout)

    table = Table(title="Change Summary")
    table.add_column("Type", style="cyan")
    table.add_column("Count")

    for change_type, count in changes.items():
        table.add_row(change_type, str(count))

    console.print(table)

    console.print("\n[bold]Diff preview:[/bold]")
    # Show first 100 lines of diff
    lines = diff_result.stdout.split("\n")[:100]
    for line in lines:
        if line.startswith("+"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(line)

    if len(diff_result.stdout.split("\n")) > 100:
        console.print("[dim]... (truncated)[/dim]")


def analyze_diff(diff: str) -> dict:
    """Analyze diff content."""
    changes = {
        "additions": 0,
        "deletions": 0,
        "files": 0,
    }

    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            changes["additions"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            changes["deletions"] += 1
        elif line.startswith("diff --git"):
            changes["files"] += 1

    return changes