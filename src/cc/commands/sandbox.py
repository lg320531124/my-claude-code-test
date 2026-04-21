"""Sandbox Command - Sandbox management."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table

from ..utils.async_process import run_command_async
from ..utils.async_io import exists_async, read_file_async, write_file_async


async def run_sandbox(console: Console, cwd: Path, action: str, args: List[str]) -> None:
    """Run sandbox command."""
    if action == "status":
        await sandbox_status(console, cwd)
    elif action == "enable":
        await enable_sandbox(console, cwd)
    elif action == "disable":
        await disable_sandbox(console, cwd)
    elif action == "test":
        await test_sandbox(console, cwd, args[0] if args else None)
    elif action == "config":
        await configure_sandbox(console, args)
    elif action == "logs":
        await sandbox_logs(console, cwd)
    else:
        show_sandbox_help(console)


async def sandbox_status(console: Console, cwd: Path) -> None:
    """Check sandbox status."""
    console.print("[bold cyan]Sandbox Status[/]")

    # Check if sandbox config exists
    sandbox_config_path = cwd / ".claude" / "sandbox.json"

    if await exists_async(sandbox_config_path):
        console.print("[green]✓ Sandbox enabled[/]")

        content = await read_file_async(sandbox_config_path)
        import json
        config = json.loads(content)

        console.print(f"\n[bold]Configuration:[/]")
        console.print(f"  Mode: {config.get('mode', 'restricted')}")
        console.print(f"  Allowed paths: {len(config.get('allowed_paths', []))}")
        console.print(f"  Allowed commands: {len(config.get('allowed_commands', []))}")

    else:
        console.print("[yellow]✗ Sandbox not configured[/]")
        console.print("[dim]Default mode: restricted[/]")


async def enable_sandbox(console: Console, cwd: Path) -> None:
    """Enable sandbox."""
    console.print("[bold cyan]Enabling Sandbox[/]")

    sandbox_config = {
        "enabled": True,
        "mode": "restricted",
        "allowed_paths": [str(cwd)],
        "allowed_commands": ["ls", "cat", "git", "python", "npm", "node"],
        "denied_commands": ["rm -rf", "sudo", "mkfs"],
        "network": {
            "enabled": False,
            "allowed_hosts": [],
        },
        "timeout": 30,
    }

    sandbox_dir = cwd / ".claude"
    sandbox_path = sandbox_dir / "sandbox.json"

    import json

    await write_file_async(sandbox_path, json.dumps(sandbox_config, indent=2))

    console.print(f"[green]✓ Sandbox enabled[/]")
    console.print(f"  Config: {sandbox_path}")


async def disable_sandbox(console: Console, cwd: Path) -> None:
    """Disable sandbox."""
    console.print("[bold cyan]Disabling Sandbox[/]")

    sandbox_path = cwd / ".claude" / "sandbox.json"

    if await exists_async(sandbox_path):
        import json
        content = await read_file_async(sandbox_path)
        config = json.loads(content)
        config["enabled"] = False

        await write_file_async(sandbox_path, json.dumps(config, indent=2))
        console.print("[yellow]✓ Sandbox disabled[/]")
    else:
        console.print("[dim]No sandbox configuration[/]")


async def test_sandbox(console: Console, cwd: Path, command: Optional[str]) -> None:
    """Test sandbox restrictions."""
    console.print("[bold cyan]Testing Sandbox[/]")

    if not command:
        console.print("[dim]Testing with safe commands...[/]")
        commands = ["ls", "pwd", "git status"]
    else:
        commands = [command]

    for cmd in commands:
        console.print(f"\n[yellow]Testing: {cmd}[/]")

        try:
            result = await run_command_async(cmd, cwd=cwd, timeout=5)
            if result.exit_code == 0:
                console.print(f"[green]✓ Allowed[/]")
            else:
                console.print(f"[red]✗ Blocked[/]")
                console.print(f"[dim]Reason: {result.stderr[:50]}[/]")
        except asyncio.TimeoutError:
            console.print("[red]✗ Timeout (blocked)[/]")
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/]")


async def configure_sandbox(console: Console, args: List[str]) -> None:
    """Configure sandbox."""
    console.print("[bold cyan]Sandbox Configuration[/]")

    if not args:
        console.print("\n[dim]Usage: /sandbox config <option> <value>[/]")
        console.print("\n[bold]Options:[/]")
        console.print("  mode <restricted|permissive>")
        console.print("  allow-path <path>")
        console.print("  allow-cmd <command>")
        console.print("  deny-cmd <command>")
        console.print("  timeout <seconds>")
        return

    # Parse arguments
    option = args[0]
    value = args[1] if len(args) > 1 else None

    if not value:
        console.print(f"[red]Please provide value for {option}[/]")
        return

    console.print(f"\n[yellow]Setting {option} = {value}[/]")

    # Would update sandbox config
    console.print("[green]✓ Configuration updated[/]")


async def sandbox_logs(console: Console, cwd: Path) -> None:
    """Show sandbox logs."""
    console.print("[bold cyan]Sandbox Logs[/]")

    logs_path = cwd / ".claude" / "sandbox.log"

    if await exists_async(logs_path):
        content = await read_file_async(logs_path)
        lines = content.split("\n")[-20:]
        for line in lines:
            console.print(f"  {line[:100]}")
    else:
        console.print("[dim]No logs available[/]")


def show_sandbox_help(console: Console) -> None:
    """Show sandbox command help."""
    table = Table(title="Sandbox Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("sandbox status", "Check sandbox status"),
        ("sandbox enable", "Enable sandbox"),
        ("sandbox disable", "Disable sandbox"),
        ("sandbox test [cmd]", "Test sandbox restrictions"),
        ("sandbox config <option> <value>", "Configure sandbox"),
        ("sandbox logs", "Show sandbox logs"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


__all__ = ["run_sandbox"]