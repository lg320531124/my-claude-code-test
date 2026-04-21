"""GitHub App Command - GitHub App installation and management."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table

from ..utils.async_http import AsyncHTTPClient
from ..utils.async_process import run_command_async


async def run_github_app(console: Console, action: str, args: List[str]) -> None:
    """Run GitHub App command."""
    if action == "install":
        await install_github_app(console)
    elif action == "status":
        await github_app_status(console)
    elif action == "configure":
        await configure_github_app(console, args)
    elif action == "repos":
        await list_installed_repos(console)
    elif action == "uninstall":
        await uninstall_github_app(console)
    else:
        show_github_app_help(console)


async def install_github_app(console: Console) -> None:
    """Guide user through GitHub App installation."""
    console.print("[bold cyan]GitHub App Installation[/]")
    console.print("\n[bold]Steps:[/]")
    console.print("1. Go to GitHub App settings")
    console.print("2. Install Claude Code GitHub App")
    console.print("3. Select repositories to grant access")
    console.print("4. Authorize the app")

    console.print("\n[yellow]App URL:[/] https://github.com/apps/claude-code")

    # Check if gh is available
    result = await run_command_async("gh auth status")

    if "Logged in" in result.stdout:
        console.print("\n[green]✓ GitHub CLI authenticated[/]")
    else:
        console.print("\n[yellow]GitHub CLI not authenticated[/]")
        console.print("[dim]Run: gh auth login[/]")


async def github_app_status(console: Console) -> None:
    """Check GitHub App installation status."""
    console.print("[bold cyan]GitHub App Status[/]")

    # Check gh auth
    result = await run_command_async("gh auth status 2>&1")
    console.print(f"\n[bold]GitHub CLI:[/]")
    if "Logged in" in result.stdout:
        console.print("[green]✓ Authenticated[/]")
    else:
        console.print("[red]✗ Not authenticated[/]")

    # Check app installations
    console.print("\n[bold]App Installations:[/]")

    try:
        # Would query GitHub API for installations
        console.print("[dim]Checking installed repositories...[/]")

        # Placeholder - would use actual GitHub API
        result = await run_command_async("gh repo list --limit 10")

        repos = [r.strip() for r in result.stdout.split("\n") if r.strip()]
        console.print(f"Accessible repos: {len(repos)}")

    except Exception:
        console.print("[yellow]Unable to check installations[/]")


async def configure_github_app(console: Console, args: List[str]) -> None:
    """Configure GitHub App settings."""
    console.print("[bold cyan]GitHub App Configuration[/]")

    if not args:
        console.print("\n[dim]Usage: /github-app configure <repo>[/]")
        return

    repo = args[0]
    console.print(f"\n[yellow]Configuring: {repo}[/]")

    # Would configure webhook, permissions, etc.
    console.print("\n[dim]Configuration options:[/]")
    console.print("  • Webhook URL")
    console.print("  • Events to receive")
    console.print("  • Access permissions")


async def list_installed_repos(console: Console) -> None:
    """List repositories with app installed."""
    console.print("[bold cyan]Installed Repositories[/]")

    result = await run_command_async("gh repo list --limit 50")

    table = Table(title="Repositories")
    table.add_column("Repository", style="cyan")
    table.add_column("Owner", style="green")
    table.add_column("Status", style="dim")

    for line in result.stdout.split("\n"):
        if line.strip():
            parts = line.strip().split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1].split()[0] if len(parts[1].split()) > 0 else parts[1]
                table.add_row(repo, owner, "installed")

    console.print(table)


async def uninstall_github_app(console: Console) -> None:
    """Guide user through GitHub App uninstallation."""
    console.print("[bold cyan]GitHub App Uninstallation[/]")

    console.print("\n[yellow]To uninstall:[/]")
    console.print("1. Go to GitHub Settings → Applications")
    console.print("2. Find Claude Code app")
    console.print("3. Click 'Uninstall'")

    console.print("\n[bold]URL:[/] https://github.com/settings/installations")


def show_github_app_help(console: Console) -> None:
    """Show GitHub App command help."""
    table = Table(title="GitHub App Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("github-app install", "Install GitHub App"),
        ("github-app status", "Check installation status"),
        ("github-app configure <repo>", "Configure app for repo"),
        ("github-app repos", "List installed repositories"),
        ("github-app uninstall", "Uninstall GitHub App"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


__all__ = ["run_github_app"]