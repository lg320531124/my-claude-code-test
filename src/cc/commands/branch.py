"""Branch Command - Git branch management."""

from __future__ import annotations
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group("branch")
def branch_group():
    """Git branch management."""
    pass


@branch_group.command("list")
@click.option("--remote", "-r", is_flag=True, help="Show remote branches")
@click.option("--all", "-a", is_flag=True, help="Show all branches")
def list_branches(remote: bool, all: bool):
    """List branches."""
    import subprocess

    cmd = ["git", "branch"]
    if all:
        cmd.append("-a")
    elif remote:
        cmd.append("-r")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        branches = result.stdout.strip().split("\n")

        table = Table(title="Branches")
        table.add_column("Branch", style="cyan")
        table.add_column("Status", style="white")

        for branch in branches:
            branch = branch.strip()
            if branch.startswith("*"):
                table.add_row(branch[1:].strip(), "[green]current[/green]")
            else:
                table.add_row(branch, "")

        console.print(table)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error: {e.stderr}[/red]")


@branch_group.command("create")
@click.argument("name")
@click.option("--from", "-f", "from_branch", default=None, help="Create from branch")
@click.option("--switch", "-s", is_flag=True, help="Switch to new branch")
def create_branch(name: str, from_branch: Optional[str], switch: bool):
    """Create a new branch."""
    import subprocess

    cmd = ["git", "branch", name]
    if from_branch:
        cmd.append(from_branch)

    try:
        subprocess.run(cmd, check=True)
        console.print(f"[green]Created branch: {name}[/green]")

        if switch:
            subprocess.run(["git", "checkout", name], check=True)
            console.print(f"[green]Switched to: {name}[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error: {e.stderr}[/red]")


@branch_group.command("switch")
@click.argument("name")
def switch_branch(name: str):
    """Switch to a branch."""
    import subprocess

    try:
        subprocess.run(["git", "checkout", name], check=True)
        console.print(f"[green]Switched to: {name}[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error: {e.stderr}[/red]")


@branch_group.command("delete")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Force delete")
def delete_branch(name: str, force: bool):
    """Delete a branch."""
    import subprocess

    cmd = ["git", "branch", "-d" if not force else "-D", name]

    try:
        subprocess.run(cmd, check=True)
        console.print(f"[green]Deleted branch: {name}[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error: {e.stderr}[/red]")


@branch_group.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def rename_branch(old_name: str, new_name: str):
    """Rename a branch."""
    import subprocess

    try:
        subprocess.run(["git", "branch", "-m", old_name, new_name], check=True)
        console.print(f"[green]Renamed: {old_name} → {new_name}[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error: {e.stderr}[/red]")


__all__ = ["branch_group"]
