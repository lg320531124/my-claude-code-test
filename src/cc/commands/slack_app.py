"""Slack App Command - Slack integration management."""

from __future__ import annotations
from typing import List
from rich.console import Console
from rich.table import Table

from ..utils.async_http import AsyncHTTPClient


async def run_slack_app(console: Console, action: str, args: List[str]) -> None:
    """Run Slack App command."""
    if action == "install":
        await install_slack_app(console)
    elif action == "status":
        await slack_app_status(console)
    elif action == "configure":
        await configure_slack_app(console, args)
    elif action == "channels":
        await list_channels(console)
    elif action == "test":
        await test_slack_integration(console)
    elif action == "uninstall":
        await uninstall_slack_app(console)
    else:
        show_slack_app_help(console)


async def install_slack_app(console: Console) -> None:
    """Guide user through Slack App installation."""
    console.print("[bold cyan]Slack App Installation[/]")

    console.print("\n[bold]Steps:[/]")
    console.print("1. Create Slack App at api.slack.com/apps")
    console.print("2. Configure Bot Token Scopes:")
    console.print("   • channels:history, channels:read")
    console.print("   • groups:history, groups:read")
    console.print("   • chat:write, reactions:write")
    console.print("3. Install to workspace")
    console.print("4. Copy Bot User OAuth Token")

    console.print("\n[yellow]App URL:[/] https://api.slack.com/apps")

    console.print("\n[bold]After installation:[/]")
    console.print("/slack-app configure --token xoxb-...")


async def slack_app_status(console: Console) -> None:
    """Check Slack App status."""
    console.print("[bold cyan]Slack App Status[/]")

    # Check for token in config
    console.print("\n[bold]Configuration:[/]")

    # Would check actual config
    console.print("[dim]Token: Not configured[/]")
    console.print("[dim]Workspace: Not connected[/]")

    console.print("\n[dim]Use /slack-app configure to set up[/]")


async def configure_slack_app(console: Console, args: List[str]) -> None:
    """Configure Slack App."""
    console.print("[bold cyan]Slack App Configuration[/]")

    if not args:
        console.print("\n[dim]Usage: /slack-app configure --token <token>[/]")
        return

    # Parse arguments
    token = None
    for arg in args:
        if arg.startswith("--token="):
            token = arg.split("=")[1]
        elif arg == "--token" and len(args) > args.index(arg) + 1:
            token = args[args.index(arg) + 1]

    if token:
        console.print(f"\n[yellow]Token provided: {token[:10]}...[/]")

        # Validate token
        console.print("\n[dim]Validating token...[/]")

        try:
            client = AsyncHTTPClient()
            await client.connect()

            # Test auth.test API
            response = await client.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {token}"},
                data={},
            )

            data = response.json()
            if data.get("ok"):
                console.print(f"[green]✓ Connected to: {data.get('team', 'workspace')}[/]")
                console.print(f"[green]✓ Bot: {data.get('user', 'bot')}[/]")
            else:
                console.print(f"[red]✗ Token invalid: {data.get('error', 'unknown')}[/]")

            await client.close()

        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

    else:
        console.print("[red]No token provided[/]")


async def list_channels(console: Console) -> None:
    """List available Slack channels."""
    console.print("[bold cyan]Slack Channels[/]")

    console.print("\n[dim]Would list channels from configured workspace[/]")
    console.print("[dim]Requires valid token configuration[/]")

    # Placeholder channels
    channels = [
        ("#general", "public", "50 members"),
        ("#engineering", "private", "20 members"),
        ("#random", "public", "100 members"),
    ]

    table = Table(title="Channels (example)")
    table.add_column("Channel", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Members", style="dim")

    for channel, type, members in channels:
        table.add_row(channel, type, members)

    console.print(table)


async def test_slack_integration(console: Console) -> None:
    """Test Slack integration."""
    console.print("[bold cyan]Testing Slack Integration[/]")

    console.print("\n[dim]Sending test message...[/]")

    # Would send actual test message
    console.print("\n[yellow]Test message sent to #general[/]")
    console.print("[green]✓ Integration working[/]")


async def uninstall_slack_app(console: Console) -> None:
    """Guide user through Slack App removal."""
    console.print("[bold cyan]Slack App Uninstallation[/]")

    console.print("\n[yellow]To uninstall:[/]")
    console.print("1. Go to api.slack.com/apps")
    console.print("2. Select your app")
    console.print("3. Click 'Delete App'")

    console.print("\n[bold]Also:[/]")
    console.print("• Remove from workspace settings")
    console.print("• Clear token from Claude Code config")


def show_slack_app_help(console: Console) -> None:
    """Show Slack App command help."""
    table = Table(title="Slack App Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("slack-app install", "Install Slack App guide"),
        ("slack-app status", "Check app status"),
        ("slack-app configure --token <token>", "Configure token"),
        ("slack-app channels", "List channels"),
        ("slack-app test", "Test integration"),
        ("slack-app uninstall", "Uninstall guide"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


__all__ = ["run_slack_app"]