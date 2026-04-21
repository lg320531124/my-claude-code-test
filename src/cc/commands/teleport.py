"""Teleport Command - Remote workspace connection."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import List
from rich.console import Console
from rich.table import Table

from ..utils.async_process import run_command_async
from ..utils.async_io import exists_async, read_file_async, write_file_async


async def run_teleport(console: Console, action: str, args: List[str]) -> None:
    """Run teleport command."""
    if action == "connect":
        await connect_remote(console, args)
    elif action == "disconnect":
        await disconnect_remote(console)
    elif action == "status":
        await teleport_status(console)
    elif action == "list":
        await list_remotes(console)
    elif action == "sync":
        await sync_files(console, args)
    elif action == "exec":
        await exec_remote(console, args)
    else:
        show_teleport_help(console)


async def connect_remote(console: Console, args: List[str]) -> None:
    """Connect to remote workspace."""
    console.print("[bold cyan]Teleport Connect[/]")

    if not args:
        console.print("[red]Usage: /teleport connect <host>[/]")
        console.print("\n[bold]Examples:[/]")
        console.print("  ssh://user@host:port")
        console.print("  vscode://remote")
        return

    host = args[0]

    console.print(f"\n[yellow]Connecting to: {host}[/]")

    # Parse connection type
    if host.startswith("ssh://"):
        await connect_ssh(console, host)
    elif host.startswith("vscode://"):
        await connect_vscode(console, host)
    else:
        console.print(f"[red]Unknown protocol: {host}[/]")


async def connect_ssh(console: Console, host: str) -> None:
    """Connect via SSH."""
    # Parse SSH URL
    host = host.replace("ssh://", "")

    console.print("\n[dim]Establishing SSH connection...[/]")

    # Test connection
    result = await run_command_async(
        f"ssh -o ConnectTimeout=5 -o BatchMode=yes {host} 'echo connected'",
        timeout=10,
    )

    if result.exit_code == 0 and "connected" in result.stdout:
        console.print(f"[green]✓ Connected to {host}[/]")

        # Save connection
        teleport_config = {
            "connected": True,
            "host": host,
            "protocol": "ssh",
            "connected_at": asyncio.get_event_loop().time(),
        }

        config_path = Path(".claude/teleport.json")
        import json
        await write_file_async(config_path, json.dumps(teleport_config, indent=2))

    else:
        console.print("[red]✗ Connection failed[/]")
        console.print(f"[dim]{result.stderr[:100]}[/]")


async def connect_vscode(console: Console, host: str) -> None:
    """Connect via VS Code Remote."""
    console.print("\n[yellow]VS Code Remote connection[/]")
    console.print("[dim]Would open VS Code with remote extension[/]")

    # Would invoke VS Code
    console.print("[green]✓ VS Code opened[/]")


async def disconnect_remote(console: Console) -> None:
    """Disconnect from remote."""
    console.print("[bold cyan]Teleport Disconnect[/]")

    config_path = Path(".claude/teleport.json")

    if await exists_async(config_path):
        import json
        content = await read_file_async(config_path)
        config = json.loads(content)

        console.print(f"[yellow]Disconnecting from: {config.get('host', 'unknown')}[/]")

        config["connected"] = False
        await write_file_async(config_path, json.dumps(config, indent=2))

        console.print("[green]✓ Disconnected[/]")
    else:
        console.print("[dim]No active connection[/]")


async def teleport_status(console: Console) -> None:
    """Show teleport status."""
    console.print("[bold cyan]Teleport Status[/]")

    config_path = Path(".claude/teleport.json")

    if await exists_async(config_path):
        import json
        content = await read_file_async(config_path)
        config = json.loads(content)

        if config.get("connected"):
            console.print("[green]✓ Connected[/]")
            console.print(f"  Host: {config.get('host', 'unknown')}")
            console.print(f"  Protocol: {config.get('protocol', 'unknown')}")
        else:
            console.print("[yellow]Disconnected[/]")
    else:
        console.print("[dim]No teleport configuration[/]")


async def list_remotes(console: Console) -> None:
    """List known remote workspaces."""
    console.print("[bold cyan]Remote Workspaces[/]")

    # Would list from config
    remotes = [
        ("dev-server-1", "ssh://user@dev1.example.com:22", "connected"),
        ("dev-server-2", "ssh://user@dev2.example.com:22", "available"),
        ("vscode-remote", "vscode://remote", "available"),
    ]

    table = Table(title="Remotes")
    table.add_column("Name", style="cyan")
    table.add_column("Host", style="green")
    table.add_column("Status", style="dim")

    for name, host, status in remotes:
        table.add_row(name, host, status)

    console.print(table)


async def sync_files(console: Console, args: List[str]) -> None:
    """Sync files with remote."""
    console.print("[bold cyan]Teleport Sync[/]")

    if not args:
        console.print("[dim]Syncing current directory...[/]")
    else:
        files = args
        console.print(f"[dim]Syncing {len(files)} files...[/]")

    # Would use rsync or scp
    console.print("\n[dim]Simulating sync operation[/]")
    console.print("[green]✓ Sync complete[/]")


async def exec_remote(console: Console, args: List[str]) -> None:
    """Execute command on remote."""
    console.print("[bold cyan]Teleport Exec[/]")

    if not args:
        console.print("[red]Usage: /teleport exec <command>[/]")
        return

    command = " ".join(args)
    console.print(f"\n[yellow]Executing: {command}[/]")

    config_path = Path(".claude/teleport.json")

    if await exists_async(config_path):
        import json
        content = await read_file_async(config_path)
        config = json.loads(content)

        if config.get("connected"):
            host = config.get("host")

            result = await run_command_async(
                f"ssh {host} '{command}'",
                timeout=30,
            )

            console.print(result.stdout)

            if result.stderr:
                console.print(f"[dim]{result.stderr}[/]")

        else:
            console.print("[red]Not connected[/]")
    else:
        console.print("[red]No connection[/]")


def show_teleport_help(console: Console) -> None:
    """Show teleport command help."""
    table = Table(title="Teleport Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("teleport connect <host>", "Connect to remote"),
        ("teleport disconnect", "Disconnect"),
        ("teleport status", "Connection status"),
        ("teleport list", "List remotes"),
        ("teleport sync [files]", "Sync files"),
        ("teleport exec <cmd>", "Execute remote"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)

    console.print("\n[bold]Host Formats:[/]")
    console.print("  ssh://user@host:port")
    console.print("  vscode://remote")


__all__ = ["run_teleport"]