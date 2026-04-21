"""MCP command - Manage MCP servers."""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable
import asyncio

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel


async def list_mcp_async(console: Console) -> None:
    """List MCP servers."""
    from ..mcp import get_mcp_manager, show_mcp_status, show_mcp_tools

    manager = get_mcp_manager()
    await manager.load_config()

    # Show status
    show_mcp_status(console)

    # Show tools if any connected
    connected = manager.get_connected_servers()
    if connected:
        console.print("\n")
        show_mcp_tools(console)


async def connect_mcp_async(console: Console, server_name: str) -> None:
    """Connect to MCP server."""
    from ..mcp import get_mcp_manager

    manager = get_mcp_manager()
    await manager.load_config()

    if server_name not in manager.connections:
        console.print(f"[red]Server not configured: {server_name}[/red]")
        return

    conn = manager.connections[server_name]

    console.print(f"[bold]Connecting to {server_name}...[/bold]")
    result = await conn.connect()

    if result:
        console.print(f"[green]Connected to {server_name}[/green]")
        console.print(f"  Tools: {len(conn.tools)}")
        console.print(f"  Resources: {len(conn.resources)}")
    else:
        console.print(f"[red]Failed to connect to {server_name}[/red]")


async def disconnect_mcp_async(console: Console, server_name: str) -> None:
    """Disconnect from MCP server."""
    from ..mcp import get_mcp_manager

    manager = get_mcp_manager()

    if server_name not in manager.connections:
        console.print(f"[red]Server not found: {server_name}[/red]")
        return

    conn = manager.connections[server_name]
    await conn.disconnect()

    console.print(f"[green]Disconnected from {server_name}[/green]")


async def reload_mcp_async(console: Console) -> None:
    """Reload MCP configuration."""
    from ..mcp import get_mcp_manager

    manager = get_mcp_manager()

    console.print("[bold]Reloading MCP configuration...[/bold]")
    await manager.reload()

    console.print("[green]Configuration reloaded[/green]")
    show_mcp_status(console)


async def call_mcp_async(console: Console, server_name: str, tool_name: str, args: dict) -> None:
    """Call MCP tool."""
    from ..mcp import call_mcp_tool

    console.print(f"[bold]Calling {server_name}.{tool_name}...[/bold]")
    console.print(f"[dim]Args: {args}[/dim]")

    result = await call_mcp_tool(server_name, tool_name, args)

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
    else:
        console.print(Panel(
            str(result)[:500],
            title="Result",
            border_style="green",
        ))


async def add_mcp_async(console: Console, name: str, command: str, args: List[str] = []) -> None:
    """Add MCP server to config."""
    from ..mcp import start_mcp_server

    config = {
        "command": command,
        "args": args,
    }

    console.print(f"[bold]Adding MCP server: {name}[/bold]")
    console.print(f"  Command: {command}")
    console.print(f"  Args: {args}")

    result = await start_mcp_server(name, config)

    if result:
        console.print(f"[green]Added and connected: {name}[/green]")
    else:
        console.print(f"[red]Failed to connect: {name}[/red]")


def run_mcp(console: Console, action: str = "list", args: List[str] = []) -> None:
    """Run MCP command."""
    if action == "list":
        asyncio.run(list_mcp_async(console))
    elif action == "connect":
        server_name = args[0] if args else Prompt.ask("Server name")
        asyncio.run(connect_mcp_async(console, server_name))
    elif action == "disconnect":
        server_name = args[0] if args else Prompt.ask("Server name")
        asyncio.run(disconnect_mcp_async(console, server_name))
    elif action == "reload":
        asyncio.run(reload_mcp_async(console))
    elif action == "call":
        server_name = args[0] if args else Prompt.ask("Server name")
        tool_name = args[1] if len(args) > 1 else Prompt.ask("Tool name")
        # Parse args as JSON if provided
        import json
        tool_args = {}
        if len(args) > 2:
            try:
                tool_args = json.loads(args[2])
            except json.JSONDecodeError:
                tool_args = {"input": args[2]}
        asyncio.run(call_mcp_async(console, server_name, tool_name, tool_args))
    elif action == "add":
        name = args[0] if args else Prompt.ask("Server name")
        command = args[1] if len(args) > 1 else Prompt.ask("Command")
        cmd_args = args[2:] if len(args) > 2 else []
        asyncio.run(add_mcp_async(console, name, command, cmd_args))
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Actions: list, connect, disconnect, reload, call, add")
