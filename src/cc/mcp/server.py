"""MCP Server Management."""

from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from .client import get_mcp_manager


console = Console()


async def start_mcp_server(name: str, config: dict) -> bool:
    """Start a specific MCP server."""
    manager = get_mcp_manager()

    from .client import MCPConnection
    conn = MCPConnection(
        name=name,
        command=config.get("command", ""),
        args=config.get("args", []),
        env=config.get("env", {}),
    )

    manager.connections[name] = conn
    return await conn.connect()


async def stop_mcp_server(name: str) -> bool:
    """Stop a specific MCP server."""
    manager = get_mcp_manager()
    conn = manager.connections.get(name)

    if conn:
        await conn.disconnect()
        return True
    return False


async def restart_mcp_server(name: str) -> bool:
    """Restart a MCP server."""
    manager = get_mcp_manager()
    conn = manager.connections.get(name)

    if conn:
        await conn.disconnect()
        return await conn.connect()
    return False


async def list_mcp_servers() -> List[dict]:
    """List all MCP servers."""
    manager = get_mcp_manager()
    servers = []

    for name, conn in manager.connections.items():
        info = manager.get_server_info(name)
        servers.append(info)

    return servers


async def discover_mcp_tools() -> List[dict]:
    """Discover all MCP tools."""
    manager = get_mcp_manager()
    return manager.get_all_tools()


def show_mcp_status(console: Console = console) -> None:
    """Show MCP status."""
    manager = get_mcp_manager()

    table = Table(title="MCP Servers")
    table.add_column("Server", style="cyan")
    table.add_column("Status")
    table.add_column("Tools")
    table.add_column("Resources")

    for name, conn in manager.connections.items():
        status = "[green]Connected[/]" if conn.connected else "[red]Disconnected[/]"
        table.add_row(name, status, str(len(conn.tools)), str(len(conn.resources)))

    if not manager.connections:
        console.print("[dim]No MCP servers configured[/dim]")
    else:
        console.print(table)


def show_mcp_tools(console: Console = console) -> None:
    """Show available MCP tools."""
    manager = get_mcp_manager()
    tools = manager.get_all_tools()

    if not tools:
        console.print("[dim]No MCP tools available[/dim]")
        return

    table = Table(title="MCP Tools")
    table.add_column("Tool", style="cyan")
    table.add_column("Description")

    for tool in tools:
        desc = tool.get("description", "")[:50]
        table.add_row(tool["name"], desc)

    console.print(table)


async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Call MCP tool."""
    manager = get_mcp_manager()
    return await manager.call_tool(server_name, tool_name, arguments)


async def read_mcp_resource(server_name: str, uri: str) -> dict:
    """Read MCP resource."""
    manager = get_mcp_manager()
    return await manager.read_resource(server_name, uri)


class MCPServerProcess:
    """MCP server process wrapper."""

    def __init__(self, name: str, command: str, args: List[str] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Start the server."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Start reader task
            self.reader_task = asyncio.create_task(self._read_loop())

            return True
        except Exception:
            return False

    async def stop(self) -> None:
        """Stop the server."""
        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass

        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()

    async def _read_loop(self) -> None:
        """Read stdout continuously."""
        if not self.process or not self.process.stdout:
            return

        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                # Handle server output
                console.print(f"[dim]{self.name}: {line.decode().strip()}[/dim]")
        except asyncio.CancelledError:
            pass

    async def send_message(self, message: dict) -> Optional[dict]:
        """Send message to server."""
        if not self.process or not self.process.stdin:
            return None

        try:
            msg_json = json.dumps(message) + "\n"
            self.process.stdin.write(msg_json.encode())
            await self.process.stdin.drain()

            # Wait for response
            if self.process.stdout:
                response = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=10.0,
                )
                return json.loads(response.decode())
        except Exception:
            return None

        return None


class MCPResourceHandler:
    """Handles MCP resources."""

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    async def fetch(self, uri: str, use_cache: bool = True) -> Optional[Any]:
        """Fetch resource."""
        if use_cache and uri in self.cache:
            return self.cache[uri]

        # This would integrate with actual MCP server
        result = await self._fetch_from_server(uri)

        if use_cache and result:
            self.cache[uri] = result

        return result

    async def _fetch_from_server(self, uri: str) -> Optional[Any]:
        """Fetch from MCP server."""
        # Placeholder - would route to appropriate server
        return None

    def clear_cache(self) -> None:
        """Clear resource cache."""
        self.cache.clear()


class MCPToolRegistry:
    """Registry for MCP tools."""

    def __init__(self):
        self.tools: Dict[str, dict] = {}
        self.handlers: Dict[str, Any] = {}

    def register(self, name: str, schema: dict, handler: Optional[Any] = None) -> None:
        """Register a tool."""
        self.tools[name] = schema
        self.handlers[name] = handler

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        self.tools.pop(name, None)
        self.handlers.pop(name, None)

    def get_schema(self, name: str) -> Optional[dict]:
        """Get tool schema."""
        return self.tools.get(name)

    def get_handler(self, name: str) -> Optional[Any]:
        """Get tool handler."""
        return self.handlers.get(name)

    def list_tools(self) -> List[dict]:
        """List all tools."""
        return list(self.tools.values())


# Global registry
_registry: Optional[MCPToolRegistry] = None


def get_registry() -> MCPToolRegistry:
    """Get global registry."""
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry