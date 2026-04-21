"""MCP Client - Async Model Context Protocol client.

Async client for connecting to MCP servers and discovering tools/resources.
"""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from ...utils.async_process import AsyncProcess
from ...utils.async_io import read_file_async


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    timeout: float = 30.0


class MCPClient:
    """Async MCP client implementation."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: Optional[AsyncProcess] = None
        self._initialized = False
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}

    async def connect(self) -> None:
        """Connect to MCP server."""
        # Build command
        full_command = self.config.command
        if self.config.args:
            full_command += " " + " ".join(self.config.args)

        # Create process
        self._process = AsyncProcess(
            full_command,
            cwd=self.config.cwd,
            timeout=self.config.timeout,
        )

        # Start process
        await self._process.run()

        # Initialize MCP protocol
        await self._initialize()

    async def _initialize(self) -> None:
        """Initialize MCP protocol."""
        # Send initialize request
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
            },
            "clientInfo": {
                "name": "claude-code-python",
                "version": "1.0.0",
            },
        })

        # Send initialized notification
        await self._send_notification("initialized", {})

        self._initialized = True

        # Discover tools and resources
        await self._discover_tools()
        await self._discover_resources()

    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send JSON-RPC request."""
        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        # Send request
        message = json.dumps(request) + "\n"
        if self._process and self._process._process:
            self._process._process.stdin.write(message.encode())
            await self._process._process.stdin.drain()

        # Wait for response
        return await asyncio.wait_for(future, timeout=self.config.timeout)

    async def _send_notification(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> None:
        """Send JSON-RPC notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        message = json.dumps(notification) + "\n"
        if self._process and self._process._process:
            self._process._process.stdin.write(message.encode())
            await self._process._process.stdin.drain()

    async def _handle_response(self, response: Dict[str, Any]) -> None:
        """Handle JSON-RPC response."""
        request_id = response.get("id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if "error" in response:
                future.set_exception(Exception(response["error"]))
            else:
                future.set_result(response.get("result", {}))

    async def _discover_tools(self) -> None:
        """Discover available tools."""
        response = await self._send_request("tools/list", {})
        tools_data = response.get("tools", [])

        self._tools = [
            MCPTool(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
            )
            for tool in tools_data
        ]

    async def _discover_resources(self) -> None:
        """Discover available resources."""
        response = await self._send_request("resources/list", {})
        resources_data = response.get("resources", [])

        self._resources = [
            MCPResource(
                uri=res.get("uri", ""),
                name=res.get("name", ""),
                description=res.get("description"),
                mime_type=res.get("mimeType"),
            )
            for res in resources_data
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call MCP tool."""
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        return response

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read MCP resource."""
        response = await self._send_request("resources/read", {
            "uri": uri,
        })
        return response

    def get_tools(self) -> List[MCPTool]:
        """Get discovered tools."""
        return self._tools

    def get_resources(self) -> List[MCPResource]:
        """Get discovered resources."""
        return self._resources

    async def close(self) -> None:
        """Close connection."""
        if self._process:
            await self._process.kill()
            self._process = None
        self._initialized = False


async def load_mcp_servers(config_path: Path) -> List[MCPServerConfig]:
    """Load MCP server configurations from file."""
    if not config_path.exists():
        return []

    content = await read_file_async(config_path)
    config = json.loads(content)

    servers = []
    mcp_servers = config.get("mcpServers", {})

    for name, server_config in mcp_servers.items():
        servers.append(MCPServerConfig(
            name=name,
            command=server_config.get("command", ""),
            args=server_config.get("args", []),
            env=server_config.get("env", {}),
            cwd=server_config.get("cwd"),
            timeout=server_config.get("timeout", 30.0),
        ))

    return servers


class MCPManager:
    """Manage multiple MCP clients."""

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}

    async def connect_server(self, config: MCPServerConfig) -> MCPClient:
        """Connect to MCP server."""
        client = MCPClient(config)
        await client.connect()
        self._clients[config.name] = client
        return client

    async def connect_all(self, configs: List[MCPServerConfig]) -> None:
        """Connect to all servers."""
        for config in configs:
            try:
                await self.connect_server(config)
            except Exception:
                # Skip failed connections
                pass

    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get client by name."""
        return self._clients.get(name)

    def get_all_tools(self) -> Dict[str, List[MCPTool]]:
        """Get all tools from all clients."""
        return {
            name: client.get_tools()
            for name, client in self._clients.items()
        }

    def get_all_resources(self) -> Dict[str, List[MCPResource]]:
        """Get all resources from all clients."""
        return {
            name: client.get_resources()
            for name, client in self._clients.items()
        }

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call tool on specific server."""
        client = self._clients.get(server_name)
        if client:
            return await client.call_tool(tool_name, arguments)
        raise Exception(f"Server not found: {server_name}")

    async def close_all(self) -> None:
        """Close all connections."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()


__all__ = [
    "MCPClient",
    "MCPServerConfig",
    "MCPTool",
    "MCPResource",
    "MCPManager",
    "load_mcp_servers",
]