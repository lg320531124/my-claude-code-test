"""MCP command - Model Context Protocol management."""

from __future__ import annotations
import json
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table


def run_mcp(console: Console, action: str = "list") -> None:
    """Manage MCP servers."""
    config_path = Path.home() / ".claude-code-py" / "mcp.json"

    if action == "list":
        list_mcp_servers(console, config_path)
    elif action == "add":
        console.print("[yellow]Use config file to add MCP servers[/yellow]")
    elif action == "remove":
        console.print("[yellow]Use config file to remove MCP servers[/yellow]")
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


def list_mcp_servers(console: Console, config_path: Path) -> None:
    """List configured MCP servers."""
    if not config_path.exists():
        console.print("[yellow]No MCP configuration found[/yellow]")
        console.print(f"[dim]Create {config_path} to configure MCP servers[/dim]")
        return

    try:
        config = json.loads(config_path.read_text())
        servers = config.get("mcpServers", {})

        if not servers:
            console.print("[yellow]No MCP servers configured[/yellow]")
            return

        table = Table(title="MCP Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Command")
        table.add_column("Status")

        for name, server_config in servers.items():
            cmd = server_config.get("command", "unknown")
            # Check if server is running (basic check)
            status = "[dim]configured[/]"
            table.add_row(name, cmd, status)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error reading config: {e}[/red]")


def get_mcp_config_template() -> dict:
    """Get MCP config template."""
    return {
        "mcpServers": {
            "filesystem": {
                "command": "mcp-server-filesystem",
                "args": ["--root", "/path/to/project"],
            },
            "github": {
                "command": "mcp-server-github",
                "env": {"GITHUB_TOKEN": "your-token"},
            },
        }
    }
