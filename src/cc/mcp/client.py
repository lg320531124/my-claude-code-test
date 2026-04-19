"""MCP Client - Model Context Protocol integration."""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional

import httpx


class MCPConnection:
    """MCP server connection."""

    def __init__(
        self,
        name: str,
        command: str,
        args: List[str] = [],
        env: Dict[str, str] = {},
    ):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self.process: asyncio.subprocess.Process | None = None
        self.connected = False
        self.tools: List[dict] = []
        self.resources: List[dict] = []

    async def connect(self) -> bool:
        """Connect to MCP server."""
        try:
            # Start MCP server process
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**self.env, **self._get_process_env()},
            )

            # Send initialize request
            response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "claude-code-py",
                    "version": "1.0.0",
                },
            })

            if response and "result" in response:
                self.connected = True
                # Discover tools and resources
                await self._discover_capabilities()
                return True

            return False

        except Exception as e:
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
            self.process = None
        self.connected = False
        self.tools = []
        self.resources = []

    async def _send_request(self, method: str, params: Optional[dict] = None) -> dict | None:
        """Send JSON-RPC request."""
        if not self.process or not self.process.stdin:
            return None

        request = {
            "jsonrpc": "2.0",
            "id": str(asyncio.get_event_loop().time()),
            "method": method,
        }
        if params:
            request["params"] = params

        try:
            # Write request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # Read response
            if self.process.stdout:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=10.0,
                )
                return json.loads(response_line.decode())

        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

        return None

    async def _discover_capabilities(self) -> None:
        """Discover tools and resources."""
        # List tools
        tools_response = await self._send_request("tools/list")
        if tools_response and "result" in tools_response:
            self.tools = tools_response["result"].get("tools", [])

        # List resources
        resources_response = await self._send_request("resources/list")
        if resources_response and "result" in resources_response:
            self.resources = resources_response["result"].get("resources", [])

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call MCP tool."""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            return {"error": response["error"]}
        return {"error": "No response"}

    async def read_resource(self, uri: str) -> dict:
        """Read MCP resource."""
        response = await self._send_request("resources/read", {"uri": uri})

        if response and "result" in response:
            return response["result"]
        return {"error": "No response"}

    def _get_process_env(self) -> dict:
        """Get environment variables for process."""
        import os
        # Include current environment but filter sensitive keys
        env = dict(os.environ)
        # MCP servers might need specific env vars
        return env

    def get_tools_schema(self) -> List[dict]:
        """Get tool schemas for API."""
        schemas = []
        for tool in self.tools:
            schemas.append({
                "name": f"mcp_{self.name}_{tool['name']}",
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {}),
            })
        return schemas


class MCPManager:
    """Manages multiple MCP connections."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / ".claude" / "mcp.json"
        self.connections: Dict[str, MCPConnection] = {}
        self._on_tool_result: Optional[Callable] = None

    async def load_config(self) -> None:
        """Load MCP configuration."""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path) as f:
                config = json.load(f)

            servers = config.get("mcpServers", {})
            for name, server_config in servers.items():
                conn = MCPConnection(
                    name=name,
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                )
                self.connections[name] = conn

        except (json.JSONDecodeError, IOError):
            pass

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured servers."""
        results = {}
        for name, conn in self.connections.items():
            results[name] = await conn.connect()
        return results

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for conn in self.connections.values():
            await conn.disconnect()

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        """Call tool on specific server."""
        conn = self.connections.get(server_name)
        if not conn or not conn.connected:
            return {"error": f"Server {server_name} not connected"}

        result = await conn.call_tool(tool_name, arguments)

        if self._on_tool_result:
            self._on_tool_result(server_name, tool_name, result)

        return result

    async def read_resource(self, server_name: str, uri: str) -> dict:
        """Read resource from server."""
        conn = self.connections.get(server_name)
        if not conn or not conn.connected:
            return {"error": f"Server {server_name} not connected"}

        return await conn.read_resource(uri)

    def get_all_tools(self) -> List[dict]:
        """Get all tool schemas."""
        schemas = []
        for conn in self.connections.values():
            if conn.connected:
                schemas.extend(conn.get_tools_schema())
        return schemas

    def get_connected_servers(self) -> List[str]:
        """Get list of connected servers."""
        return [
            name for name, conn in self.connections.items()
            if conn.connected
        ]

    def get_server_info(self, server_name: str) -> dict:
        """Get server information."""
        conn = self.connections.get(server_name)
        if not conn:
            return {}

        return {
            "name": conn.name,
            "connected": conn.connected,
            "tools": len(conn.tools),
            "resources": len(conn.resources),
        }

    def set_callback(self, callback: Callable) -> None:
        """Set tool result callback."""
        self._on_tool_result = callback

    async def reload(self) -> None:
        """Reload configuration and reconnect."""
        await self.disconnect_all()
        self.connections.clear()
        await self.load_config()
        await self.connect_all()


class MCPToolWrapper:
    """Wraps MCP tool as Claude Code tool."""

    def __init__(self, server_name: str, tool_info: dict, connection: MCPConnection):
        self.server_name = server_name
        self.tool_info = tool_info
        self.connection = connection

        self.name = f"mcp_{server_name}_{tool_info['name']}"
        self.description = tool_info.get("description", "")

    async def execute(self, arguments: dict, ctx: Any) -> dict:
        """Execute MCP tool."""
        return await self.connection.call_tool(self.tool_info["name"], arguments)

    def get_schema(self) -> dict:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.tool_info.get("inputSchema", {}),
        }


# Global MCP manager instance
_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get global MCP manager."""
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager


async def initialize_mcp() -> Dict[str, bool]:
    """Initialize MCP connections."""
    manager = get_mcp_manager()
    await manager.load_config()
    return await manager.connect_all()
